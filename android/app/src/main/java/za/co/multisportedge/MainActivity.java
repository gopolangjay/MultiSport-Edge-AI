package za.co.multisportedge;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

public class MainActivity extends Activity {
    private WebView webView;
    private static final String APP_URL = "https://multisport-edge-ai.onrender.com/";
    private static final String APP_HOST = "multisport-edge-ai.onrender.com";

    @Override protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(Color.rgb(4,16,20));
        getWindow().setNavigationBarColor(Color.rgb(4,16,20));
        webView = new WebView(this);
        webView.setBackgroundColor(Color.rgb(4,16,20));
        setContentView(webView);
        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true); s.setDomStorageEnabled(true); s.setDatabaseEnabled(true);
        s.setLoadWithOverviewMode(true); s.setUseWideViewPort(true);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        webView.setWebChromeClient(new WebChromeClient());
        webView.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri=request.getUrl(); String host=uri.getHost();
                if (host!=null && (host.equals(APP_HOST)||host.endsWith(".onrender.com"))) return false;
                try { startActivity(new Intent(Intent.ACTION_VIEW, uri)); } catch(Exception ignored) {}
                return true;
            }
            @Override public void onPageFinished(WebView view,String url) { super.onPageFinished(view,url); }
        });
        if(savedInstanceState==null) webView.loadUrl("file:///android_asset/v2-shell.html"); else webView.restoreState(savedInstanceState);
        webView.postDelayed(() -> { if(webView!=null) webView.loadUrl(APP_URL); }, 1800);
    }
    @Override protected void onSaveInstanceState(Bundle outState){webView.saveState(outState);super.onSaveInstanceState(outState);}
    @Override public void onBackPressed(){if(webView!=null&&webView.canGoBack())webView.goBack();else super.onBackPressed();}
}
