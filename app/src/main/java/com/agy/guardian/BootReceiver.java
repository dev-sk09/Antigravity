package com.agy.guardian;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.util.Log;

import com.agy.core.CoreServiceLauncher;

/** Restarts the core after a reboot or an app update when work is pending. */
public final class BootReceiver extends BroadcastReceiver {

    @Override
    public void onReceive(Context context, Intent intent) {
        String action = intent != null ? intent.getAction() : null;
        if (!Intent.ACTION_BOOT_COMPLETED.equals(action)
                && !Intent.ACTION_MY_PACKAGE_REPLACED.equals(action)) {
            return;
        }
        if (!ServiceKeeper.shouldKeepAlive(context)) {
            return;
        }
        Log.i("BootReceiver", action + ": restarting core for pending tasks");
        try {
            CoreServiceLauncher.start(context);
        } catch (Exception e) {
            ServiceKeeper.scheduleRestart(context, 5_000);
        }
    }
}
