package za.co.multisportedge;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

public class MainActivity extends Activity {
    private WebView webView;
    private static final String APP_HOST = "multisport-edge-ai.onrender.com";
    private static final String APP_ORIGIN = "https://" + APP_HOST;

    private static final String FETCH_BRIDGE =
            "window.fetch=(function(){return function(input,init){" +
            "var u=typeof input==='string'?input:(input&&input.url)||'';" +
            "if(u.indexOf('" + APP_ORIGIN + "/')===0){try{" +
            "var r=JSON.parse(AndroidApi.get(u.substring('" + APP_ORIGIN + "'.length)));" +
            "return Promise.resolve(new Response(r.body,{status:r.status,headers:{'Content-Type':r.contentType||'application/json'}}));" +
            "}catch(e){return Promise.reject(e);}}" +
            "return Promise.reject(new Error('External fetch blocked by Android API bridge'));" +
            "};})();";

    @Override protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(Color.rgb(4,16,20));
        getWindow().setNavigationBarColor(Color.rgb(4,16,20));
        webView = new WebView(this);
        webView.setBackgroundColor(Color.rgb(4,16,20));
        setContentView(webView);

        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setLoadWithOverviewMode(true);
        s.setUseWideViewPort(true);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);

        webView.addJavascriptInterface(new ProductionApiBridge(), "AndroidApi");
        webView.setWebChromeClient(new WebChromeClient());
        webView.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                String host = uri.getHost();
                if (host != null && host.equals(APP_HOST)) return false;
                if ("file".equals(uri.getScheme())) return false;
                try { startActivity(new Intent(Intent.ACTION_VIEW, uri)); } catch (Exception ignored) {}
                return true;
            }

            @Override public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                if (url != null && url.startsWith("file:///android_asset/")) {
                    view.evaluateJavascript(FETCH_BRIDGE + "load();", null);
                }
            }
        });

        if (savedInstanceState == null) {
            webView.loadUrl("file:///android_asset/v2-shell.html");
        } else {
            webView.restoreState(savedInstanceState);
        }
    }

    private static class ProductionApiBridge {
        @JavascriptInterface
        public String get(String path) {
            if (path == null || !path.startsWith("/")) return envelope(400, "application/json", "{\"error\":\"invalid_path\"}");
            if (!(path.equals("/health") || path.startsWith("/v1/"))) {
                return envelope(403, "application/json", "{\"error\":\"path_not_allowed\"}");
            }
            HttpURLConnection connection = null;
            try {
                URL url = new URL(APP_ORIGIN + path);
                connection = (HttpURLConnection) url.openConnection();
                connection.setRequestMethod("GET");
                connection.setConnectTimeout(15000);
                connection.setReadTimeout(30000);
                connection.setInstanceFollowRedirects(true);
                connection.setRequestProperty("Accept", "application/json");
                connection.setRequestProperty("User-Agent", "MultiSport-Edge-AI-Android/2");
                int status = connection.getResponseCode();
                String type = connection.getContentType();
                InputStream stream = status >= 400 ? connection.getErrorStream() : connection.getInputStream();
                String body = readAll(stream);
                return envelope(status, type == null ? "application/json" : type, body);
            } catch (Exception e) {
                return envelope(599, "application/json", "{\"error\":\"android_api_unreachable\",\"detail\":\"" + jsonEscape(e.getClass().getSimpleName()) + "\"}");
            } finally {
                if (connection != null) connection.disconnect();
            }
        }

        private static String readAll(InputStream stream) throws Exception {
            if (stream == null) return "";
            StringBuilder out = new StringBuilder();
            try (BufferedReader reader = new BufferedReader(new InputStreamReader(stream, StandardCharsets.UTF_8))) {
                String line;
                while ((line = reader.readLine()) != null) out.append(line);
            }
            return out.toString();
        }

        private static String envelope(int status, String type, String body) {
            return "{\"status\":" + status + ",\"contentType\":\"" + jsonEscape(type) + "\",\"body\":\"" + jsonEscape(body) + "\"}";
        }

        private static String jsonEscape(String value) {
            if (value == null) return "";
            return value.replace("\\", "\\\\").replace("\"", "\\\"").replace("\r", "\\r").replace("\n", "\\n").replace("\t", "\\t");
        }
    }

    @Override protected void onSaveInstanceState(Bundle outState) {
        webView.saveState(outState);
        super.onSaveInstanceState(outState);
    }

    @Override public void onBackPressed() {
        if (webView != null && webView.canGoBack()) webView.goBack();
        else super.onBackPressed();
    }
}
