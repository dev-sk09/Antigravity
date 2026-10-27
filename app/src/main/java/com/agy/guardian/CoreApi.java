package com.agy.guardian;

import com.agy.core.CoreRuntimeState;

import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import javax.net.ssl.HttpsURLConnection;

/**
 * Minimal Connect-JSON client for the core's LanguageServerService. The core
 * accepts application/json on the same loopback HTTPS port the WebView uses;
 * the bundled core certificate is already trusted via network_security_config.
 */
final class CoreApi {

    private static final String SERVICE = "exa.language_server_pb.LanguageServerService";
    private static final int CONNECT_TIMEOUT_MS = 3000;
    private static final int READ_TIMEOUT_MS = 30000;

    private CoreApi() {
    }

    static boolean isReady() {
        return CoreRuntimeState.serverUrl != null && CoreRuntimeState.csrfToken != null;
    }

    static JSONObject call(String method, JSONObject body) throws Exception {
        URL url = new URL("https://127.0.0.1:" + CoreRuntimeState.httpsPort + "/" + SERVICE + "/" + method);
        HttpsURLConnection conn = (HttpsURLConnection) url.openConnection();
        try {
            conn.setConnectTimeout(CONNECT_TIMEOUT_MS);
            conn.setReadTimeout(READ_TIMEOUT_MS);
            conn.setUseCaches(false);
            conn.setDoOutput(true);
            conn.setRequestMethod("POST");
            conn.setRequestProperty("Content-Type", "application/json");
            conn.setRequestProperty("x-codeium-csrf-token", CoreRuntimeState.csrfToken);
            byte[] payload = (body != null ? body : new JSONObject()).toString().getBytes(StandardCharsets.UTF_8);
            try (OutputStream out = conn.getOutputStream()) {
                out.write(payload);
            }
            int code = conn.getResponseCode();
            InputStream in = code >= 400 ? conn.getErrorStream() : conn.getInputStream();
            String text = in != null ? readAll(in) : "";
            if (code >= 400) {
                throw new Exception(method + " HTTP " + code + ": " + text);
            }
            return text.isEmpty() ? new JSONObject() : new JSONObject(text);
        } finally {
            conn.disconnect();
        }
    }

    private static String readAll(InputStream in) throws Exception {
        try (InputStream input = in) {
            ByteArrayOutputStream buf = new ByteArrayOutputStream();
            byte[] chunk = new byte[8192];
            int n;
            while ((n = input.read(chunk)) != -1) {
                buf.write(chunk, 0, n);
            }
            return buf.toString("UTF-8");
        }
    }
}
