package com.agy.core;

import android.app.Service;
import android.content.Intent;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.util.Log;

import com.agy.runtime.RuntimeManager;

import java.io.File;
import java.security.SecureRandom;
import java.util.concurrent.TimeUnit;

/**
 * Foreground host for the patched core (language_server). Holds a wake lock,
 * streams the process log to files/logs/core.log, and publishes serverUrl once
 * ready.
 */
public final class CoreServerService extends Service {

    private static final String TAG = "CoreServer";

    private RuntimeManager runtime;
    private WakeLockHolder wakeLock;
    private OpenUrlWatcher openUrlWatcher;
    private CoreProcessSupervisor supervisor;
    private com.agy.guardian.TaskGuardian taskGuardian;
    private com.agy.log.LogRingBuffer logBuffer;
    private com.agy.gateway.SystemGatewayServer gatewayServer;
    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    private volatile boolean destroyed;

    @Override
    public void onCreate() {
        super.onCreate();
        runtime = new RuntimeManager(this);
        logBuffer = new com.agy.log.LogRingBuffer();
        // One secret for this launch, shared by the gateway and the agent sidecar.
        CoreRuntimeState.gatewayToken = newToken();
        gatewayServer = new com.agy.gateway.SystemGatewayServer(
                this, logBuffer, com.agy.BuildConfig.GATEWAY_PORT, CoreRuntimeState.gatewayToken);
        gatewayServer.start();

        Log.i(TAG, "state paths: HOME=" + getFilesDir().getAbsolutePath()
                + " appData=" + runtime.getAppDataDir().getAbsolutePath()
                + " projects=" + runtime.getProjectsDir().getAbsolutePath()
                + " runtime=" + runtime.getRuntimeDir().getAbsolutePath());
        CoreRuntimeState.httpsPort = runtime.getHttpsPort();
        CoreRuntimeState.csrfToken = runtime.getCsrfToken();
        CoreRuntimeState.restarting = false;
        CoreRuntimeState.lastError = null;
        CoreRuntimeState.serverUrl = null;

        ForegroundNotification.start(this);
        wakeLock = new WakeLockHolder();
        wakeLock.acquire(this);

        openUrlWatcher = new OpenUrlWatcher(this);
        openUrlWatcher.start();

        supervisor = new CoreProcessSupervisor(this, runtime, openUrlWatcher, logBuffer,
                this::onSupervisorTerminated);
        supervisor.start();

        taskGuardian = new com.agy.guardian.TaskGuardian(this);
        taskGuardian.start();

        startBackgroundDaemon();
        startModelAgent();
    }

    /** Env shared by the sidecar helpers: the same base the daemon uses. */
    private void applyEnv(ProcessBuilder pb) {
        String files = getFilesDir().getAbsolutePath();
        pb.directory(getFilesDir());
        pb.environment().put("PATH", files + "/usr/bin:" + System.getenv("PATH"));
        pb.environment().put("HOME", files);
        pb.environment().put("PREFIX", files + "/usr");
        pb.environment().put("LD_LIBRARY_PATH", files + "/usr/lib");
    }

    /** Local Agent sidecar (agy-agent): OpenAI-compatible model router + tools. */
    private void startModelAgent() {
        new Thread(() -> {
            try {
                Thread.sleep(1800);
                File agentBin = new File(getFilesDir(), "usr/bin/agy-agent");
                if (!agentBin.canExecute()) {
                    return;
                }
                Log.i(TAG, "Starting Local Agent sidecar...");
                ProcessBuilder pb = new ProcessBuilder(
                        agentBin.getAbsolutePath(), "start",
                        "--port", String.valueOf(com.agy.BuildConfig.AGENT_PORT));
                applyEnv(pb);
                // The sidecar's own token and the gateway token (for its device
                // tool) are passed in the environment, never on the command line.
                String token = CoreRuntimeState.gatewayToken;
                if (token != null) {
                    pb.environment().put("AGY_AGENT_TOKEN", token);
                    pb.environment().put("AGY_GATEWAY_TOKEN", token);
                }
                pb.start();
            } catch (Exception e) {
                Log.w(TAG, "Failed to start agy-agent: " + e.getMessage());
            }
        }, "AgyAgentStarter").start();
    }

    private void stopModelAgent() {
        try {
            File agentBin = new File(getFilesDir(), "usr/bin/agy-agent");
            if (agentBin.canExecute()) {
                Log.i(TAG, "Stopping Local Agent sidecar...");
                ProcessBuilder pb = new ProcessBuilder(agentBin.getAbsolutePath(), "stop");
                applyEnv(pb);
                Process p = pb.start();
                if (!p.waitFor(1500, TimeUnit.MILLISECONDS)) {
                    p.destroyForcibly();
                }
            }
        } catch (Exception e) {
            Log.w(TAG, "Failed to stop agy-agent: " + e.getMessage());
        }
    }

    private void startBackgroundDaemon() {
        new Thread(() -> {
            try {
                // Give runtime environment a brief moment to stabilize
                Thread.sleep(1500);
                File daemonBin = new File(getFilesDir(), "usr/bin/agy-daemon");
                if (daemonBin.canExecute()) {
                    Log.i(TAG, "Starting autonomous background daemon...");
                    ProcessBuilder pb = new ProcessBuilder(daemonBin.getAbsolutePath(), "start");
                    pb.directory(getFilesDir());
                    pb.environment().put("PATH", getFilesDir().getAbsolutePath() + "/usr/bin:" + System.getenv("PATH"));
                    pb.environment().put("HOME", getFilesDir().getAbsolutePath());
                    pb.environment().put("PREFIX", getFilesDir().getAbsolutePath() + "/usr");
                    pb.environment().put("LD_LIBRARY_PATH", getFilesDir().getAbsolutePath() + "/usr/lib");
                    pb.start();
                }
            } catch (Exception e) {
                Log.w(TAG, "Failed to start agy-daemon: " + e.getMessage());
            }
        }, "AgyDaemonStarter").start();
    }

    private void stopBackgroundDaemon() {
        try {
            File daemonBin = new File(getFilesDir(), "usr/bin/agy-daemon");
            if (daemonBin.canExecute()) {
                Log.i(TAG, "Stopping autonomous background daemon...");
                ProcessBuilder pb = new ProcessBuilder(daemonBin.getAbsolutePath(), "stop");
                pb.directory(getFilesDir());
                pb.environment().put("PATH", getFilesDir().getAbsolutePath() + "/usr/bin:" + System.getenv("PATH"));
                pb.environment().put("HOME", getFilesDir().getAbsolutePath());
                pb.environment().put("PREFIX", getFilesDir().getAbsolutePath() + "/usr");
                pb.environment().put("LD_LIBRARY_PATH", getFilesDir().getAbsolutePath() + "/usr/lib");
                Process p = pb.start();
                if (!p.waitFor(1500, TimeUnit.MILLISECONDS)) {
                    Log.w(TAG, "agy-daemon stop timed out after 1500ms; destroying forcibly");
                    p.destroyForcibly();
                }
            }
        } catch (Exception e) {
            Log.w(TAG, "Failed to stop agy-daemon: " + e.getMessage());
        }
    }

    private void onSupervisorTerminated() {
        mainHandler.post(new Runnable() {
            @Override
            public void run() {
                if (destroyed) {
                    return;
                }
                CoreRuntimeState.serverUrl = null;
                CoreRuntimeState.restarting = false;
                if (CoreRuntimeState.lastError == null) {
                    CoreRuntimeState.lastError = "core supervisor stopped unexpectedly";
                }
                if (wakeLock != null) {
                    wakeLock.release();
                }
                if (runtime != null) {
                    runtime.stopNetworkMonitor();
                }
                if (openUrlWatcher != null) {
                    openUrlWatcher.stop();
                }
                ForegroundNotification.update(CoreServerService.this,
                        "Core stopped — open app to retry");
                // If a task is still unfinished, come back on our own instead
                // of waiting for the user to reopen the app.
                if (com.agy.guardian.ServiceKeeper.shouldKeepAlive(CoreServerService.this)) {
                    com.agy.guardian.ServiceKeeper.scheduleRestart(CoreServerService.this, 3_000);
                }
            }
        });
    }

    @Override
    public void onDestroy() {
        stopBackgroundDaemon();
        stopModelAgent();
        if (gatewayServer != null) {
            gatewayServer.stop();
        }
        destroyed = true;
        mainHandler.removeCallbacksAndMessages(null);
        if (taskGuardian != null) {
            taskGuardian.stop();
        }
        // If the OS is killing us while work is pending, schedule a comeback.
        if (com.agy.guardian.ServiceKeeper.shouldKeepAlive(this)) {
            com.agy.guardian.ServiceKeeper.scheduleRestart(this, 3_000);
        }
        // Intentional stop: the watchdog must not treat the exit as a crash.
        if (supervisor != null) {
            supervisor.stop();
        }
        if (openUrlWatcher != null) {
            openUrlWatcher.stop();
        }
        if (wakeLock != null) {
            wakeLock.release();
        }
        if (runtime != null) {
            runtime.stopNetworkMonitor();
        }
        CoreRuntimeState.serverUrl = null;
        CoreRuntimeState.lastError = null;
        CoreRuntimeState.restarting = false;
        super.onDestroy();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        return START_STICKY;
    }

    @Override
    public void onTaskRemoved(Intent rootIntent) {
        super.onTaskRemoved(rootIntent);
        Log.i(TAG, "onTaskRemoved: Task swiped from recents; maintaining CoreServerService alive in background");
        ForegroundNotification.update(this, "Gemini Premium running in background");
    }

    /** 32 random bytes as lowercase hex, for the gateway/agent shared secret. */
    private static String newToken() {
        byte[] random = new byte[32];
        new SecureRandom().nextBytes(random);
        char[] hex = "0123456789abcdef".toCharArray();
        char[] out = new char[random.length * 2];
        for (int i = 0; i < random.length; i++) {
            int v = random[i] & 0xff;
            out[i * 2] = hex[v >>> 4];
            out[i * 2 + 1] = hex[v & 0x0f];
        }
        return new String(out);
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
