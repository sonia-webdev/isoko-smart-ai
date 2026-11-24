"""Build web/index.html from web/template.html + web/app.jsx.   Run: python tools/build_web.py"""
import os
HERE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")
tpl = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
app = open(os.path.join(HERE, "app.jsx"), encoding="utf-8").read()
open(os.path.join(HERE, "index.html"), "w", encoding="utf-8").write(tpl.replace("/*APP*/", app))
print("Wrote web/index.html")
