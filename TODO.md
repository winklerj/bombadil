* browser tests
    * check external links?
    * add LTL specs support
    * detect changes using mutation observers?
* proxy
    * better IDs
        * hash of (file id, seq number)
    * use etag as file id first, otherwise hash the bytes
    * instrument inline scripts in html?
    * cache instrumented responses
        * respect cache headers? or just infinite lifetime?

# ideas

* concurrent testing with:
    * multiple independent browsers
    * multiple tabs in a single browser
* faults:
    * paused/blurred tab
    * network request reordering, delays, etc (not necessary with antithesis fault injector?)
    * clear cookies, application state, etc

