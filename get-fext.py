import json
import os
import platform
import site
import sysconfig
from tempfile import NamedTemporaryFile

from urllib.request import urlopen
from zipfile import ZipFile

RELEASES_URL = 'https://api.github.com/repos/fextpkg/cli/releases'


def _check_win_comp(platform_tag):
    return platform_tag == "win_amd64"


def _compare_glibc_ver(major, minor):
    glibc_major, glibc_minor = map(int, platform.libc_ver()[1].split('.'))
    return glibc_major >= int(major) and glibc_minor >= int(minor)


def _check_linux_comp(platform_tag):
    data = platform_tag.split('_', 3)  # [platform, glibc_major_ver, glibc_minor_ver, arch]

    return data[0] == "manylinux" and data[3] == 'x86_64' and _compare_glibc_ver(data[1], data[2])


def _get_comp_check_func():
    system, machine = platform.system(), platform.machine()
    if system == "Windows" and machine == "AMD64":
        return _check_win_comp
    elif system == "Linux" and machine == "x86_64":
        return _check_linux_comp
    else:
        raise Exception(f'Unsupported platform: {system} {machine}')


def get_releases():
    with urlopen(RELEASES_URL) as r:
        return json.loads(r.read().decode())


def get_download_link():
    comp_func = _get_comp_check_func()

    for release in get_releases():
        for asset in release['assets']:
            data = asset['name'].split('-')  # [name, version, py_tag, abi_tag, platform_tag]
            if comp_func(data[4][:-4]):  # select platform tag and remove '.whl'
                print(f'Found Fext: {data[1]}')
                return asset['browser_download_url']


def download(url):
    print('Downloading...')
    with urlopen(url) as r:
        f = NamedTemporaryFile(mode='w+b', delete=False)
        f.write(r.read())
        return f


def extract(file):
    print('Extracting...')
    with ZipFile(file.name) as zip_file:
        site_packages = site.getusersitepackages()
        os.makedirs(site_packages, mode=0o755, exist_ok=True)
        for f in zip_file.filelist:
            if 'scripts' in f.filename:
                path = os.path.join(sysconfig.get_path('scripts'),
                                    'fext.exe' if platform.system() == 'Windows' else 'fext')
                open(path, 'wb').write(zip_file.read(f))
                os.chmod(path, 0o755)
            else:
                zip_file.extract(f, site_packages)


def install(url):
    f = download(url)
    extract(f)
    f.close()
    os.unlink(f.name)


if __name__ == '__main__':
    download_link = get_download_link()
    if not download_link:
        raise Exception('Unable to find Fext compatible version. Try to upgrade your system')

    install(download_link)
