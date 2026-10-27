package com.agy.guardian;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Context;
import android.net.ConnectivityManager;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.net.NetworkInfo;
import android.os.Build;
import android.util.Log;

import com.agy.core.CoreRuntimeState;
import com.agy.core.ForegroundNotification;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.Set;
import java.util.UUID;

/**
 * Watches agent tasks (cascades) and resumes the ones that stopped without
 * finishing: the core crashed or was restarted mid-run, the app process was
 * killed, or the run ended with an error such as a network failure. Waits for a
 * validated network before resuming, gives up after {@link #MAX_RESUMES}
 * attempts, and never resumes a task the user stopped.
 */
public final class TaskGuardian {

    private static final String TAG = "TaskGuardian";

    static final int MAX_RESUMES = 5;
    private static final long TICK_ACTIVE_MS = 5_000;
    private static final long TICK_IDLE_MS = 15_000;
    /** Backoff before resume N (0-based): 5s, 30s, 2m, 5m, 10m. */
    private static final long[] BACKOFF_MS = {5_000, 30_000, 120_000, 300_000, 600_000};

    private static final String ALERT_CHANNEL = "guardian_alerts";
    private static final int ALERT_ID = 1002;

    static final String RESUME_PROMPT =
            "[Auto-resume] Your previous run was interrupted (app restart, crash or network loss). "
            + "First check what is already done (files, command output, your task list or plan), "
            + "then continue the original task from where it stopped and finish it. "
            + "Do not redo steps that are already complete.";

    /** Identifies this process; a task last seen running under another id was cut off. */
    private static final String PROCESS_ID = UUID.randomUUID().toString();

    private final Service service;
    private final Context context;
    private volatile boolean running;
    private Thread thread;
    private final Set<String> alerted = new HashSet<>();

    public TaskGuardian(Service service) {
        this.service = service;
        this.context = service.getApplicationContext();
    }

    public synchronized void start() {
        if (running) {
            return;
        }
        running = true;
        thread = new Thread(this::loop, "AgyTaskGuardian");
        thread.setDaemon(true);
        thread.start();
    }

    public synchronized void stop() {
        running = false;
        if (thread != null) {
            thread.interrupt();
        }
    }

    private static String currentRunId() {
        return PROCESS_ID + "/" + CoreRuntimeState.readyGeneration;
    }

    private void loop() {
        Log.i(TAG, "started");
        while (running) {
            long sleep = TICK_IDLE_MS;
            try {
                if (TaskJournal.isEnabled(context) && CoreApi.isReady()) {
                    sleep = tick() ? TICK_ACTIVE_MS : TICK_IDLE_MS;
                }
            } catch (Exception e) {
                Log.w(TAG, "tick failed: " + e.getMessage());
            }
            try {
                Thread.sleep(sleep);
            } catch (InterruptedException e) {
                break;
            }
        }
        Log.i(TAG, "stopped");
    }

    /** @return true while any task is running or waiting to be resumed. */
    private boolean tick() throws Exception {
        JSONObject resp = CoreApi.call("GetAllCascadeTrajectories", new JSONObject());
        JSONObject summaries = resp.optJSONObject("trajectorySummaries");
        if (summaries == null) {
            summaries = new JSONObject();
        }
        String runId = currentRunId();
        boolean busy = false;
        int waitingForNetwork = 0;

        Iterator<String> ids = summaries.keys();
        while (ids.hasNext()) {
            String id = ids.next();
            JSONObject s = summaries.optJSONObject(id);
            if (s == null || "CORTEX_TRAJECTORY_SOURCE_SUBAGENT".equals(s.optString("source"))) {
                continue;
            }
            if (isActive(s)) {
                TaskJournal.Entry e = TaskJournal.get(context, id);
                if (e == null) {
                    e = new TaskJournal.Entry();
                    e.cascadeId = id;
                }
                e.runId = runId;
                e.stepCount = s.optInt("stepCount", 0);
                e.summary = s.optString("summary", "");
                TaskJournal.put(context, e);
                alerted.remove(id);
                busy = true;
                continue;
            }

            TaskJournal.Entry e = TaskJournal.get(context, id);
            if (e == null) {
                continue;
            }
            String reason = s.optString("latestExecutorTerminationReason", "");
            if (s.optBoolean("killed") || "EXECUTOR_TERMINATION_REASON_USER_CANCELED".equals(reason)) {
                Log.i(TAG, "user stopped " + id + "; not resuming");
                TaskJournal.remove(context, id);
                continue;
            }
            if (hasWaitingSteps(s)) {
                // Paused for the user's approval: resuming would bypass the user.
                TaskJournal.remove(context, id);
                alert(id, "Task needs your input", label(e));
                continue;
            }
            boolean cutOff = !runId.equals(e.runId);
            boolean errored = s.optBoolean("interrupted")
                    || "EXECUTOR_TERMINATION_REASON_ERROR".equals(reason);
            if (!cutOff && !errored) {
                Log.i(TAG, "task finished: " + id);
                TaskJournal.remove(context, id);
                continue;
            }

            busy = true;
            if (e.resumes >= MAX_RESUMES) {
                TaskJournal.remove(context, id);
                alert(id, "Task stopped after " + MAX_RESUMES + " resume attempts", label(e));
                continue;
            }
            long wait = BACKOFF_MS[Math.min(e.resumes, BACKOFF_MS.length - 1)];
            if (System.currentTimeMillis() - e.lastResumeAt < wait) {
                continue;
            }
            if (!hasValidatedNetwork()) {
                waitingForNetwork++;
                continue;
            }
            resume(e, runId, cutOff ? "core restarted" : "run ended with error");
        }

        // Forget tasks the core no longer knows (deleted conversations).
        List<TaskJournal.Entry> journaled = TaskJournal.list(context);
        for (TaskJournal.Entry e : journaled) {
            if (!summaries.has(e.cascadeId)) {
                TaskJournal.remove(context, e.cascadeId);
            }
        }

        if (waitingForNetwork > 0) {
            ForegroundNotification.update(service,
                    "Waiting for network to resume " + waitingForNetwork + " task(s)");
        }
        return busy;
    }

    private void resume(TaskJournal.Entry e, String runId, String why) {
        JSONObject config = TaskJournal.configFor(context, e.cascadeId);
        if (config == null) {
            // Without the UI's cascadeConfig the core has no plan model and fails.
            if (!alerted.contains(e.cascadeId)) {
                alert(e.cascadeId, "Open the app and say \"continue\"", label(e));
            }
            e.lastResumeAt = System.currentTimeMillis();
            TaskJournal.put(context, e);
            return;
        }
        try {
            JSONObject item = new JSONObject();
            item.put("text", RESUME_PROMPT);
            JSONObject req = new JSONObject();
            req.put("cascadeId", e.cascadeId);
            req.put("items", new JSONArray().put(item));
            req.put("cascadeConfig", config);
            CoreApi.call("SendUserCascadeMessage", req);
            e.resumes++;
            e.lastResumeAt = System.currentTimeMillis();
            e.runId = runId;
            TaskJournal.put(context, e);
            Log.i(TAG, "resumed " + e.cascadeId + " (" + why + "), attempt " + e.resumes);
            ForegroundNotification.update(service, "Resumed: " + label(e));
        } catch (Exception ex) {
            e.lastResumeAt = System.currentTimeMillis();
            TaskJournal.put(context, e);
            Log.w(TAG, "resume failed for " + e.cascadeId + ": " + ex.getMessage());
        }
    }

    private static boolean isActive(JSONObject s) {
        String status = s.optString("status", "");
        return "CASCADE_RUN_STATUS_RUNNING".equals(status)
                || "CASCADE_RUN_STATUS_BUSY".equals(status)
                || "CASCADE_RUN_STATUS_CANCELING".equals(status)
                || s.optBoolean("notFullyIdle");
    }

    private static boolean hasWaitingSteps(JSONObject s) {
        Object w = s.opt("waitingSteps");
        if (w instanceof JSONArray) {
            return ((JSONArray) w).length() > 0;
        }
        return w instanceof JSONObject && ((JSONObject) w).length() > 0;
    }

    private static String label(TaskJournal.Entry e) {
        String s = e.summary != null && !e.summary.isEmpty() ? e.summary : e.cascadeId;
        return s.length() > 80 ? s.substring(0, 80) + "…" : s;
    }

    @SuppressWarnings("deprecation")
    private boolean hasValidatedNetwork() {
        try {
            ConnectivityManager cm = (ConnectivityManager) context.getSystemService(Context.CONNECTIVITY_SERVICE);
            if (cm == null) {
                return true;
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                Network n = cm.getActiveNetwork();
                NetworkCapabilities caps = n != null ? cm.getNetworkCapabilities(n) : null;
                return caps != null
                        && caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
                        && caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED);
            }
            NetworkInfo info = cm.getActiveNetworkInfo();
            return info != null && info.isConnected();
        } catch (Exception e) {
            return true;
        }
    }

    private void alert(String cascadeId, String title, String text) {
        alerted.add(cascadeId);
        try {
            NotificationManager nm = (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
            if (nm == null) {
                return;
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                nm.createNotificationChannel(new NotificationChannel(
                        ALERT_CHANNEL, "Task alerts", NotificationManager.IMPORTANCE_DEFAULT));
            }
            Notification.Builder b = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
                    ? new Notification.Builder(context, ALERT_CHANNEL)
                    : new Notification.Builder(context);
            int icon = context.getResources().getIdentifier("ic_notification", "drawable", context.getPackageName());
            nm.notify(ALERT_ID, b.setContentTitle(title)
                    .setContentText(text)
                    .setSmallIcon(icon != 0 ? icon : android.R.drawable.stat_notify_error)
                    .setAutoCancel(true)
                    .build());
        } catch (Exception ignored) {
        }
    }
}
