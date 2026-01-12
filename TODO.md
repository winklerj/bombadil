* browser tests
    * check external links?
    * add LTL specs support
    * detect changes using mutation observers?
* proxy
    * instrument inline scripts in html?
    * cache instrumented responses
        * respect cache headers? or just infinite lifetime? probably needs to
          respect because there _could_ be dynamically generated scripts, even
          if weird.

# ideas

* concurrent testing with:
    * multiple independent browsers
    * multiple tabs in a single browser
* faults:
    * paused/blurred tab
    * network request reordering, delays, etc (not necessary with antithesis fault injector?)
    * clear cookies, application state, etc

