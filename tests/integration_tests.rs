use axum::Router;
use tempfile::TempDir;
use tower_http::services::ServeDir;
use url::Url;

use antithesis_browser::{browser::BrowserOptions, runner::run_test};

async fn run_browser_test(name: &str, expected_error_substring: Option<&str>) {
    let app = Router::new().fallback_service(ServeDir::new("./tests"));

    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
    let addr = listener.local_addr().unwrap();

    tokio::spawn(async move {
        axum::serve(listener, app).await.unwrap();
    });

    let origin =
        Url::parse(&format!("http://localhost:{}/{}", addr.port(), name,))
            .unwrap();
    let user_data_directory = TempDir::new().unwrap();

    let result = run_test(
        origin,
        BrowserOptions {
            headless: true,
            user_data_directory: user_data_directory.path().to_path_buf(),
            width: 800,
            height: 600,
        },
    )
    .await;
    match (result, expected_error_substring) {
        (Err(err), Some(expected_substring)) => {
            if !err.to_string().contains(expected_substring) {
                panic!("expected error message not found in: {}", err);
            }
        }
        (Ok(_), None) => {}
        (Err(err), None) => {
            panic!("unexpected error: {}", err);
        }
        (Ok(_), Some(_)) => {
            panic!("expected error but got success");
        }
    }
}

#[tokio::test]
async fn test_console_error() {
    run_browser_test("console-error", Some("oh no you pressed all of them"))
        .await;
}

#[tokio::test]
async fn test_links() {
    run_browser_test("links", Some("got 404 at localhost")).await;
}

#[tokio::test]
async fn test_uncaught_exception() {
    run_browser_test(
        "uncaught-exception",
        Some("oh no you pressed all of them"),
    )
    .await;
}

#[tokio::test]
async fn test_unhandled_promise_rejection() {
    run_browser_test(
        "unhandled-promise-rejection",
        Some("oh no you pressed all of them"),
    )
    .await;
}
