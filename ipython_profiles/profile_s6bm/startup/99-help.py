print(f'Enter {__file__}...')
# document functions defined in the profile

def list_predefined_vars():
    print(f"🙊: These are the predefined vars:")
    for key, val in keywords_vars.items():
        print(f"\t{key}:\t{val}")
    print()

def list_predefined_func():
    print(f"🙊: These are the predefined functions:")
    for key, val in keywords_func.items():
        print(f"\t{key}:\t{val}")
    print()

apstools.utils.print_RE_md()
apstools.utils.show_ophyd_symbols()
list_predefined_vars()
list_predefined_func()

print(f"""
🐉: Greetings again, {USERNAME}@{HOSTNAME}!
    You should consider using init_tomo() to switch to
        dryrun: hardware testing
        production: data collection
    before running the experiment with
    >> RE(tomo_scan(config_file)).
    {'🔥'*60}
""")