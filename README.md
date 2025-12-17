# antithesis_browser

A prototype of generative browser testing.

## Running tests

```bash
cargo run -- test https://example.com
```

Run headless:

```bash
cargo run -- test https://example.com --headless
```

See debug logs:

```bash
RUST_LOG=antithesis_browser=debug cargo run -- test https://example.com --headless
```
