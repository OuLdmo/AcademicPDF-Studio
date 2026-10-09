"""Install free English→Chinese local model by explicit user invocation.
Run: python -m pip install -r requirements-free.txt
     python tools/install_argos_model.py
The model download uses the Argos public package index; subsequent translation is offline.
"""
from __future__ import annotations

def main():
    from argostranslate import package
    print('Updating Argos package index (internet required once) ...')
    package.update_package_index()
    options=[p for p in package.get_available_packages() if p.from_code=='en' and p.to_code=='zh']
    if not options:
        raise RuntimeError('No en→zh package in current Argos index; try again later.')
    item=options[0]
    print('Downloading Argos en→zh model ...')
    package.install_from_path(item.download())
    from argostranslate import translate
    print('Installed:', translate.translate('Hello world.', 'en', 'zh'))

if __name__=='__main__':
    main()
