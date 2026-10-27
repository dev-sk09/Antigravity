package com.agy;

import android.app.Application;
import android.util.Log;

/**
 * Application entry point for Gemini Premium / Antigravity.
 * Installs robust process-level safeguards to keep background AI execution alive.
 */
public class AgyApplication extends Application {

    private static final String TAG = "AgyApplication";

    @Override
    public void onCreate() {
        super.onCreate();
        final Thread.UncaughtExceptionHandler defaultHandler = Thread.getDefaultUncaughtExceptionHandler();
        Thread.setDefaultUncaughtExceptionHandler((thread, throwable) -> {
            Log.e(TAG, "Uncaught exception on thread: " + thread.getName(), throwable);
            // If the exception originated on a background worker thread, suppress process termination
            // so the core server and ongoing AI agent sessions continue running uninterrupted.
            if (thread.getId() != getMainLooper().getThread().getId()) {
                Log.w(TAG, "Suppressed background worker crash to preserve CoreServerService session");
                return;
            }
            if (defaultHandler != null) {
                defaultHandler.uncaughtException(thread, throwable);
            }
        });
    }
}
