"""
    quart-jsglue
    ~~~~~~~~~~~~~
    Quart-JSGlue helps hook up your Quart application nicely with the front end.

    :author: Gonzalo Peralta
    :email: peraltag@gmail.com
    :license: MIT
    
    Copyright (c) 2021 Gonzalo Peralta
    
    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:
    
    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.
    
    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.
    
    ~~~~~~~~~~~~~
    Based on Flask-JSGlue:
    :author: Stewart Park
    :email: hello@stewartjpark.com
    :license: MIT
    
    Copyright (c) 2015 Stewart Park
    ~~~~~~~~~~~~~
    The changes we made are:
    - Add asynchronous support for serve_js.
    - Change JSGLUE_NAMESPACE from Flask to Quart.
"""

from markupsafe import Markup
import re
import json

JSGLUE_JS_PATH = '/jsglue.js'
JSGLUE_NAMESPACE = 'Quart'
rule_parser = re.compile(r'<(.+?)>')
splitter = re.compile(r'<.+?>')


def get_routes(app):
    output = []
    for r in app.url_map.iter_rules():
        endpoint = r.endpoint
        rule = r.rule
        rule_args = [x.split(':')[-1] for x in rule_parser.findall(rule)]
        rule_tr = splitter.split(rule)
        output.append((endpoint, rule_tr, rule_args))
    return sorted(output, key=lambda x: len(x[1]), reverse=True)


class JSGlue(object):
    jsglue_make_response = None
    jsglue_url_for = None

    def __init__(self, app=None, **kwargs):
        self.app = app
        if app is not None:
            self.init_app(app, **kwargs)

    def init_app(self, app):
        self.app = app
        from quart import make_response, url_for
        JSGlue.jsglue_make_response = make_response
        JSGlue.jsglue_url_for = url_for

        @app.route(JSGLUE_JS_PATH)
        async def serve_js():
            return await JSGlue.jsglue_make_response(
                (self.generate_js(), 200,
                 {'Content-Type': 'text/javascript; charset=utf-8'})
            )

        @app.context_processor
        def context_processor():
            return {'JSGlue': JSGlue}

    def generate_js(self):
        rules = get_routes(self.app)
        return """
var %s = new (function(){
  'use strict';
  return {
    '_endpoints': %s,
    'url_for': function (endpoint, rule) {
      if (typeof rule === "undefined") rule = {};
      else if (typeof(rule) !== "object") {
        // rule *must* be an Object, anything else is wrong
        throw {name: "ValueError", message: "type for 'rule' must be Object, got: " + typeof(rule)};
      }

      var has_everything = false,
        url = "";

      var is_absolute = false,
        has_anchor = false,
        has_scheme;
      var anchor = "",
        scheme = "";

      if (rule['_external'] === true) {
        is_absolute = true;
        scheme = location.protocol.split(':')[0];
        delete rule['_external'];
      }

      if ('_scheme' in rule) {
        if (is_absolute) {
          scheme = rule['_scheme'];
          delete rule['_scheme'];
        } else {
          throw {
            name: "ValueError",
            message: "_scheme is set without _external."
          };
        }
      }

      if ('_anchor' in rule) {
        has_anchor = true;
        anchor = rule['_anchor'];
        delete rule['_anchor'];
      }

      for (var i in this._endpoints) {
        if (endpoint == this._endpoints[i][0]) {
          var url = '';
          var j = 0;
          var has_everything = true;
          var used = {};
          for (var j = 0; j < this._endpoints[i][2].length; j++) {
            var t = rule[this._endpoints[i][2][j]];
            if (typeof t === "undefined") {
              has_everything = false;
              break;
            }
            url += this._endpoints[i][1][j] + t;
            used[this._endpoints[i][2][j]] = true;
          }
          if (has_everything) {
            if (this._endpoints[i][2].length != this._endpoints[i][1].length)
              url += this._endpoints[i][1][j];

            var first = true;
            for (var r in rule) {
              if (r[0] != '_' && !(r in used)) {
                if (first) {
                  url += '?';
                  first = false;
                } else {
                  url += '&';
                }
                url += r + '=' + rule[r];
              }
            }
            if (has_anchor) {
              url += "#" + anchor;
            }

            if (is_absolute) {
              return scheme + "://" + location.host + url;
            } else {
              return url;
            }
          }
        }
      }

      throw {
        name: 'BuildError',
        message: "Endpoint '" + endpoint + "' does not exist or you have passed incorrect parameters " + JSON.stringify(rule)
      };
    }
  };
});""" % (JSGLUE_NAMESPACE, json.dumps(rules))

    @staticmethod
    def include():
        js_path = JSGlue.jsglue_url_for('serve_js')
        return Markup('<script src="%s" type="text/javascript"></script>') % (js_path,)

