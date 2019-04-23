import helper
import os
import shutil
import settings
import translate
import webassets

from jinja2 import Environment, FileSystemLoader

extensions = ['jinja2.ext.i18n']

def read_file(file):
    with open(file, 'r') as f:
        return f.read()

class Site(object):
    def __init__(self, languages, searchpath, renderpath, staticpath, css_bundles, js_bundles = {}, data = {}):
        self.languages = languages
        self.lang = languages[0]
        self.context = {}
        self.searchpath = searchpath
        self.renderpath = renderpath
        self.staticpath = staticpath
        self.cssout = renderpath+'/media/css'
        self.css_bundles = css_bundles
        self.js_bundles = js_bundles
        self.jsout = renderpath+'/media/js'
        self.data = data

    def _text_dir(self):
        textdir = 'ltr'
        if self.lang in settings.LANGUAGES_BIDI:
            textdir = 'rtl'
        return textdir

    def _set_context(self):
        self.context = {'LANG': self.lang,
                        'DIR': self._text_dir() }

    def _setup_env(self):
        load = FileSystemLoader(self.searchpath)
        self._env = Environment(loader=load, extensions=extensions)
        self._env.filters["markdown"] = helper.safe_markdown
        self._env.filters["f"] = helper.f
        self._env.filters["l10n_format_date"] = helper.l10n_format_date

    def _concat_js(self):
        for bundle_name, files in self.js_bundles.iteritems():
            bundle_path = self.jsout+'/'+bundle_name+'.js'

            js_string = '\n'.join(read_file(settings.ASSETS + '/' + file) for file in files)
            with open(bundle_path, 'w') as f:
                f.write(js_string)

    def _switch_lang(self, lang):
        self.lang = lang
        self._set_context()
        self._env.globals.update(self.context)
        translator = translate.gettext_object(lang)
        self._env.install_gettext_translations(translator)
        self._env.globals.update(translations=translator.get_translations(), l10n_css=translator.l10n_css)

    def build_assets(self):
        shutil.rmtree(self.renderpath+'/media', ignore_errors=True)
        shutil.copytree(self.staticpath, self.renderpath+'/media')
        env = webassets.Environment(load_path=[settings.ASSETS], directory=self.cssout, url=settings.MEDIA_URL, cache=False, manifest=False)
        for k, v in self.css_bundles.iteritems():
            reg = webassets.Bundle(*v, filters='less', output=k+'.css')
            env.register(k, reg)
            env[k].urls()
        if self.js_bundles:
            self._concat_js()

    def render(self):
        outpath = os.path.join(self.renderpath, self.lang)
        for template in self._env.list_templates():
            if not template.startswith("_"):
                filepath = os.path.join(outpath, template)
                # Make sure the output directory exists.
                filedir = os.path.dirname(filepath)
                if not os.path.exists(filedir):
                    os.makedirs(filedir)
                t = self._env.get_template(template)
                t.stream().dump(filepath)

    def build_site(self):
        self._setup_env()
        self._env.globals.update(settings=settings, **helper.contextfunctions)
        if self.data:
            self._env.globals.update(self.data)
        for lang in self.languages:
            self._switch_lang(lang)
            self.render()
        self.build_assets()
