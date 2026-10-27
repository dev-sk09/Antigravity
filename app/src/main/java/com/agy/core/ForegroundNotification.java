package com.agy.core;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.pm.ServiceInfo;
import android.os.Build;

/** Builds and updates the low-importance ongoing core notification. */
public final class ForegroundNotification {

    public static final int NOTIFICATION_ID = 1001;
    public static final String CHANNEL_ID = "core_channel";

    private ForegroundNotification() {
    }

    public static void start(Service service) {
        NotificationManager manager =
                (NotificationManager) service.getSystemService(Service.NOTIFICATION_SERVICE);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O && manager != null) {
            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID, "Core", NotificationManager.IMPORTANCE_LOW);
            manager.createNotificationChannel(channel);
        }
        Notification notification = build(service, "Core running");
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            service.startForeground(NOTIFICATION_ID, notification,
                    ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC);
        } else {
            service.startForeground(NOTIFICATION_ID, notification);
        }
    }

    public static void update(Service service, String status) {
        NotificationManager manager =
                (NotificationManager) service.getSystemService(Service.NOTIFICATION_SERVICE);
        if (manager != null) {
            manager.notify(NOTIFICATION_ID, build(service, status));
        }
    }

    private static Notification build(Service service, String status) {
        int icon = service.getResources().getIdentifier(
                "ic_notification", "drawable", service.getPackageName());
        if (icon == 0) {
            icon = android.R.drawable.stat_notify_sync;
        }
        android.content.Intent intent = new android.content.Intent(service, com.agy.ui.MainActivity.class);
        intent.setFlags(android.content.Intent.FLAG_ACTIVITY_SINGLE_TOP | android.content.Intent.FLAG_ACTIVITY_CLEAR_TOP);
        int flags = android.app.PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            flags |= android.app.PendingIntent.FLAG_IMMUTABLE;
        }
        android.app.PendingIntent pendingIntent = android.app.PendingIntent.getActivity(service, 0, intent, flags);

        String title;
        try {
            int titleId = service.getResources().getIdentifier("app_name", "string", service.getPackageName());
            title = titleId != 0 ? service.getString(titleId) : "Gemini Premium";
        } catch (Exception e) {
            title = "Gemini Premium";
        }

        Notification.Builder builder = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
                ? new Notification.Builder(service, CHANNEL_ID)
                : new Notification.Builder(service);
        return builder
                .setContentTitle(title)
                .setContentText(status)
                .setSmallIcon(icon)
                .setContentIntent(pendingIntent)
                .setOngoing(true)
                .build();
    }
}
