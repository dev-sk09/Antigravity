package com.agy.guardian;

import android.app.AlarmManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.os.SystemClock;
import android.util.Log;

import com.agy.core.CoreServerService;

/**
 * Brings the core service back after the process dies. targetSdk 28 exempts the
 * app from the Android 12 background foreground-service start ban, so an alarm
 * can start it directly.
 */
public final class ServiceKeeper {

    private static final String TAG = "ServiceKeeper";
    private static final int REQUEST_CODE = 4711;

    private ServiceKeeper() {
    }

    /** Should the service come back on its own right now? */
    public static boolean shouldKeepAlive(Context context) {
        return TaskJournal.isEnabled(context) && TaskJournal.hasActiveTasks(context);
    }

    public static void scheduleRestart(Context context, long delayMs) {
        try {
            Context app = context.getApplicationContext();
            Intent intent = new Intent(app, CoreServerService.class);
            int flags = PendingIntent.FLAG_UPDATE_CURRENT;
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                flags |= PendingIntent.FLAG_IMMUTABLE;
            }
            PendingIntent pi = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
                    ? PendingIntent.getForegroundService(app, REQUEST_CODE, intent, flags)
                    : PendingIntent.getService(app, REQUEST_CODE, intent, flags);
            AlarmManager am = (AlarmManager) app.getSystemService(Context.ALARM_SERVICE);
            if (am == null) {
                return;
            }
            long at = SystemClock.elapsedRealtime() + delayMs;
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                am.setExactAndAllowWhileIdle(AlarmManager.ELAPSED_REALTIME_WAKEUP, at, pi);
            } else {
                am.setExact(AlarmManager.ELAPSED_REALTIME_WAKEUP, at, pi);
            }
            Log.i(TAG, "service restart scheduled in " + delayMs + "ms");
        } catch (Exception e) {
            Log.w(TAG, "cannot schedule restart: " + e.getMessage());
        }
    }
}
