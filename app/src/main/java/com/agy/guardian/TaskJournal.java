package com.agy.guardian;

import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONObject;

import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;

/**
 * Durable record of agent tasks (cascades) the guardian has seen running, plus
 * the last cascadeConfig the UI sent for each one. Survives process death so a
 * restarted service knows what was unfinished.
 */
public final class TaskJournal {

    private static final String PREFS = "agy_task_guardian";
    private static final String KEY_TASKS = "tasks";
    private static final String KEY_CONFIGS = "configs";
    private static final String KEY_LAST_CONFIG = "last_config";
    private static final String KEY_ENABLED = "auto_resume_enabled";

    /** One unfinished task. */
    static final class Entry {
        String cascadeId;
        String runId;       // core run in which it was last seen running
        int stepCount;      // step count when last seen running
        int resumes;        // auto-resumes since the user last spoke or it finished
        long lastResumeAt;
        String summary;

        JSONObject toJson() throws Exception {
            JSONObject o = new JSONObject();
            o.put("runId", runId);
            o.put("stepCount", stepCount);
            o.put("resumes", resumes);
            o.put("lastResumeAt", lastResumeAt);
            o.put("summary", summary != null ? summary : "");
            return o;
        }

        static Entry fromJson(String id, JSONObject o) {
            Entry e = new Entry();
            e.cascadeId = id;
            e.runId = o.optString("runId", "");
            e.stepCount = o.optInt("stepCount", 0);
            e.resumes = o.optInt("resumes", 0);
            e.lastResumeAt = o.optLong("lastResumeAt", 0);
            e.summary = o.optString("summary", "");
            return e;
        }
    }

    private static final Object LOCK = new Object();

    private TaskJournal() {
    }

    private static SharedPreferences prefs(Context context) {
        return context.getApplicationContext().getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    public static boolean isEnabled(Context context) {
        return prefs(context).getBoolean(KEY_ENABLED, true);
    }

    public static void setEnabled(Context context, boolean enabled) {
        prefs(context).edit().putBoolean(KEY_ENABLED, enabled).commit();
    }

    public static boolean hasActiveTasks(Context context) {
        return !list(context).isEmpty();
    }

    static List<Entry> list(Context context) {
        synchronized (LOCK) {
            List<Entry> out = new ArrayList<>();
            JSONObject all = readObject(context, KEY_TASKS);
            Iterator<String> keys = all.keys();
            while (keys.hasNext()) {
                String id = keys.next();
                JSONObject o = all.optJSONObject(id);
                if (o != null) {
                    out.add(Entry.fromJson(id, o));
                }
            }
            return out;
        }
    }

    static Entry get(Context context, String cascadeId) {
        synchronized (LOCK) {
            JSONObject o = readObject(context, KEY_TASKS).optJSONObject(cascadeId);
            return o != null ? Entry.fromJson(cascadeId, o) : null;
        }
    }

    static void put(Context context, Entry entry) {
        synchronized (LOCK) {
            try {
                JSONObject all = readObject(context, KEY_TASKS);
                all.put(entry.cascadeId, entry.toJson());
                prefs(context).edit().putString(KEY_TASKS, all.toString()).commit();
            } catch (Exception ignored) {
            }
        }
    }

    static void remove(Context context, String cascadeId) {
        synchronized (LOCK) {
            JSONObject all = readObject(context, KEY_TASKS);
            if (all.has(cascadeId)) {
                all.remove(cascadeId);
                prefs(context).edit().putString(KEY_TASKS, all.toString()).commit();
            }
        }
    }

    /** Called from the WebView bridge each time the user sends a message. */
    public static void saveConfig(Context context, String cascadeId, String configJson) {
        if (configJson == null || configJson.isEmpty()) {
            return;
        }
        synchronized (LOCK) {
            try {
                JSONObject config = new JSONObject(configJson);
                JSONObject all = readObject(context, KEY_CONFIGS);
                if (cascadeId != null && !cascadeId.isEmpty()) {
                    all.put(cascadeId, config);
                }
                prefs(context).edit()
                        .putString(KEY_CONFIGS, all.toString())
                        .putString(KEY_LAST_CONFIG, config.toString())
                        .commit();
                // The user just spoke to this task: refill its resume budget.
                if (cascadeId != null) {
                    JSONObject tasks = readObject(context, KEY_TASKS);
                    JSONObject t = tasks.optJSONObject(cascadeId);
                    if (t != null) {
                        t.put("resumes", 0);
                        tasks.put(cascadeId, t);
                        prefs(context).edit().putString(KEY_TASKS, tasks.toString()).commit();
                    }
                }
            } catch (Exception ignored) {
            }
        }
    }

    /** The task's own config, else the last config the UI used for any task. */
    static JSONObject configFor(Context context, String cascadeId) {
        synchronized (LOCK) {
            JSONObject own = readObject(context, KEY_CONFIGS).optJSONObject(cascadeId);
            if (own != null) {
                return own;
            }
            try {
                String last = prefs(context).getString(KEY_LAST_CONFIG, null);
                return last != null ? new JSONObject(last) : null;
            } catch (Exception e) {
                return null;
            }
        }
    }

    private static JSONObject readObject(Context context, String key) {
        try {
            String raw = prefs(context).getString(key, null);
            return raw != null ? new JSONObject(raw) : new JSONObject();
        } catch (Exception e) {
            return new JSONObject();
        }
    }
}
