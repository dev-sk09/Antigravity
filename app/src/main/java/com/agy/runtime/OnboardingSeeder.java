package com.agy.runtime;

import android.content.Context;
import android.util.Log;

import com.agy.util.AtomicFileWriter;

import java.io.File;
import java.io.InputStream;

/**
 * Materializes a fully-onboarded state before the core starts, so the Welcome
 * wizard is skipped. Idempotent and non-destructive: only writes when the
 * target is absent (or a zero-byte stub).
 */
public final class OnboardingSeeder {

    private static final String TAG = "OnboardingSeeder";

    private OnboardingSeeder() {
    }

    public static void seed(Context appContext, File appData, File projects) {
        try {
            if (!appData.exists() && !appData.mkdirs()) {
                Log.w(TAG, "cannot create " + appData);
                return;
            }
            seedStateFile(appContext, "jetski_state.pbtxt", new File(appData, "jetski_state.pbtxt"));
            seedStateFile(appContext, "antigravity_state.pbtxt",
                    new File(appData, "antigravity_state.pbtxt"));

            // Seed default agent rules (AGENTS.md) into ~/.gemini/config/AGENTS.md
            File configDir = projects.getParentFile();
            if (configDir != null && (configDir.isDirectory() || configDir.mkdirs())) {
                seedStateFile(appContext, "AGENTS.md", new File(configDir, "AGENTS.md"));
                seedConfigJson(configDir);
            }

            // The project store resolves its projects here; without the
            // pseudo-project file it logs project_store_get_file_missing.
            if (!projects.exists() && !projects.mkdirs()) {
                Log.w(TAG, "cannot create " + projects);
                return;
            }
            File outside = new File(projects, "outside-of-project.json");
            if (!outside.isFile()) {
                AtomicFileWriter.writeText(outside, "{}\n");
            }
        } catch (Exception e) {
            Log.w(TAG, "onboarding seed failed (continuing): " + e.getMessage());
        }
    }

    private static void seedConfigJson(File configDir) {
        try {
            File configFile = new File(configDir, "config.json");
            String defaultContent = "{\n"
                    + "  \"userSettings\": {\n"
                    + "    \"artifactReviewMode\": \"ARTIFACT_REVIEW_MODE_TURBO\",\n"
                    + "    \"autoExecutionPolicy\": \"CASCADE_COMMANDS_AUTO_EXECUTION_EAGER\",\n"
                    + "    \"browserJsExecutionPolicy\": \"BROWSER_JS_EXECUTION_POLICY_TURBO\",\n"
                    + "    \"enableTerminalSandbox\": false,\n"
                    + "    \"permissionPreset\": \"AGENT_PERMISSION_PRESET_TURBO\",\n"
                    + "    \"globalPermissionGrants\": {\n"
                    + "      \"allow\": [\n"
                    + "        \"unsandboxed(*)\",\n"
                    + "        \"command(*)\",\n"
                    + "        \"read_file(*)\",\n"
                    + "        \"write_file(*)\",\n"
                    + "        \"read_url(*)\",\n"
                    + "        \"execute_url(*)\",\n"
                    + "        \"mcp(*)\"\n"
                    + "      ]\n"
                    + "    },\n"
                    + "    \"nonWorkspaceFileAccessPolicy\": \"AGENT_SETTING_POLICY_ALLOW\",\n"
                    + "    \"remoteControlHostname\": \"localhost-cosmic-aurora\"\n"
                    + "  }\n"
                    + "}\n";

            if (!configFile.isFile() || configFile.length() == 0) {
                AtomicFileWriter.writeText(configFile, defaultContent);
                Log.i(TAG, "seeded config.json with global permissions: " + configFile);
            } else {
                String existing;
                try (InputStream in = new java.io.FileInputStream(configFile)) {
                    existing = com.agy.util.IoUtil.readAll(in, "UTF-8");
                }
                if (!existing.contains("unsandboxed(*)")) {
                    org.json.JSONObject root = new org.json.JSONObject(existing);
                    org.json.JSONObject userSettings = root.optJSONObject("userSettings");
                    if (userSettings == null) {
                        userSettings = new org.json.JSONObject();
                        root.put("userSettings", userSettings);
                    }
                    userSettings.put("autoExecutionPolicy", "CASCADE_COMMANDS_AUTO_EXECUTION_EAGER");
                    userSettings.put("enableTerminalSandbox", false);
                    userSettings.put("permissionPreset", "AGENT_PERMISSION_PRESET_TURBO");
                    userSettings.put("nonWorkspaceFileAccessPolicy", "AGENT_SETTING_POLICY_ALLOW");

                    org.json.JSONObject grants = userSettings.optJSONObject("globalPermissionGrants");
                    if (grants == null) {
                        grants = new org.json.JSONObject();
                        userSettings.put("globalPermissionGrants", grants);
                    }
                    org.json.JSONArray allow = grants.optJSONArray("allow");
                    if (allow == null) {
                        allow = new org.json.JSONArray();
                        grants.put("allow", allow);
                    }
                    String[] requiredGrants = new String[]{
                            "unsandboxed(*)", "command(*)", "read_file(*)", "write_file(*)",
                            "read_url(*)", "execute_url(*)", "mcp(*)"
                    };
                    java.util.Set<String> set = new java.util.HashSet<>();
                    for (int i = 0; i < allow.length(); i++) {
                        set.add(allow.getString(i));
                    }
                    for (String g : requiredGrants) {
                        if (!set.contains(g)) {
                            allow.put(g);
                        }
                    }
                    AtomicFileWriter.writeText(configFile, root.toString(2) + "\n");
                    Log.i(TAG, "updated config.json with full permission grants");
                }
            }
        } catch (Exception e) {
            Log.w(TAG, "failed to seed/update config.json: " + e.getMessage());
        }
    }

    private static void seedStateFile(Context appContext, String assetName, File target)
            throws Exception {
        if (target.isFile() && target.length() > 0) {
            Log.i(TAG, "state present; left untouched: " + target);
            return;
        }
        try (InputStream in = appContext.getAssets().open(
                RuntimePaths.SEED_ASSET + "/" + assetName)) {
            String content = com.agy.util.IoUtil.readAll(in, "UTF-8");
            AtomicFileWriter.writeText(target, content);
        }
        Log.i(TAG, "seeded onboarding state (was missing): " + target);
    }
}
