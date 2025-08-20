import os
import re
import shutil
import winreg
import subprocess
import sys
import ctypes
import glob
from typing import List, Dict


class PythonUninstaller:
    def __init__(self):
        self.installations = []
        self.verbose = True
        # Python特有的安装路径模式
        self.patterns = [
            (r'C:\\Python[0-9]+', "官方安装"),
            (r'C:\\Program Files\\Python[0-9]+', "Program Files安装"),
            (r'%USERPROFILE%\\AppData\\Local\\Programs\\Python', "用户目录安装"),
            (r'.*conda.*', "Conda环境"),
            (r'.*virtualenv.*', "虚拟环境")
        ]

    def log(self, message: str) -> None:
        if self.verbose:
            print(message)

    def detect_installations(self) -> List[Dict[str, str]]:
        """检测所有Python安装"""
        self._check_standard_installs()
        self._check_registry()
        self._check_environment_paths()
        self._check_virtualenvs()
        return self.installations

    def _check_standard_installs(self):
        """检查标准安装路径"""
        for pattern, desc in self.patterns:
            expanded = os.path.expandvars(pattern)
            for path in glob.glob(expanded):
                if os.path.exists(path):
                    self._validate_python_path(path, desc)

    def _validate_python_path(self, path: str, source: str):
        """验证是否为有效的Python安装"""
        python_exe = os.path.join(path, 'python.exe')
        if not os.path.exists(python_exe):
            python_exe = os.path.join(path, 'Scripts', 'python.exe')

        if os.path.exists(python_exe):
            version = self._get_python_version(python_exe)
            install_type = self._determine_install_type(path)

            if not any(install['path'] == path for install in self.installations):
                self.installations.append({
                    'path': path,
                    'version': version,
                    'type': install_type,
                    'source': source,
                    'executable': python_exe
                })
                self.log(f"发现: {install_type} {version} @ {path} ({source})")

    def _get_python_version(self, python_exe: str) -> str:
        """获取Python版本"""
        try:
            result = subprocess.run(
                [python_exe, '--version'],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return result.stdout.strip() or result.stderr.strip()
        except Exception as e:
            return f"版本获取失败: {str(e)}"

    def _determine_install_type(self, path: str) -> str:
        """判断安装类型"""
        path_lower = path.lower()
        if 'conda' in path_lower:
            return 'Conda'
        if 'virtualenv' in path_lower or 'venv' in path_lower:
            return 'Virtualenv'
        if 'appdata' in path_lower:
            return '用户安装'
        return '系统安装'

    def _check_registry(self):
        """检查注册表安装项"""
        self.log("\n检查注册表中的Python安装...")
        reg_locations = [
            ('SOFTWARE\\Python', 'PythonCore'),
            ('SOFTWARE\\Wow6432Node\\Python', 'PythonCore'),
            ('SOFTWARE\\ContinuumAnalytics', 'Anaconda')
        ]

        for base_key, subkey in reg_locations:
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base_key) as key:
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        version_key = winreg.EnumKey(key, i)
                        try:
                            with winreg.OpenKey(key, f"{version_key}\\InstallPath") as ip_key:
                                path = winreg.QueryValueEx(ip_key, '')[0]
                                self._validate_python_path(path, '注册表')
                        except WindowsError:
                            continue
            except WindowsError:
                continue

    def _check_environment_paths(self):
        """检查环境变量中的Python"""
        self.log("\n检查环境变量中的Python...")
        path_var = os.environ.get('PATH', '')
        for path in path_var.split(';'):
            if path and ('python' in path.lower() or 'conda' in path.lower()):
                self._validate_python_path(path, 'PATH环境变量')

    def _check_virtualenvs(self):
        """检测虚拟环境"""
        self.log("\n扫描虚拟环境...")
        search_paths = [
            os.path.expanduser('~'),
            'C:\\',
            'D:\\'
        ]

        for search_path in search_paths:
            for root, dirs, _ in os.walk(search_path):
                if 'pyvenv.cfg' in dirs or 'Scripts' in dirs:
                    self._validate_python_path(root, '虚拟环境')
                # 检查常见虚拟环境目录名
                for dir_name in dirs:
                    if dir_name.lower() in ('venv', 'virtualenv', '.venv'):
                        self._validate_python_path(os.path.join(root, dir_name), '虚拟环境')

    def uninstall(self):
        """执行卸载操作"""
        if not self.installations:
            self.log("\n没有可卸载的Python安装")
            return

        self.log("\n=== 开始卸载 ===")
        self._run_uninstallers()
        self._remove_installation_dirs()
        self._clean_environment()
        self.log("\n=== 卸载完成 ===")

    def _run_uninstallers(self):
        """运行官方卸载程序"""
        self.log("\n运行官方卸载程序...")
        for install in self.installations:
            if install['type'] in ('系统安装', '用户安装'):
                uninstaller = os.path.join(install['path'], 'Uninstall.exe')
                if os.path.exists(uninstaller):
                    try:
                        self.log(f"正在卸载: {install['path']}")
                        subprocess.run([uninstaller, '/quiet'], shell=True, check=True)
                    except subprocess.CalledProcessError as e:
                        self.log(f"卸载失败: {install['path']} - {str(e)}")

    def _remove_installation_dirs(self):
        """删除安装目录"""
        self.log("\n删除安装目录...")
        for install in self.installations:
            try:
                if os.path.exists(install['path']):
                    self.log(f"正在删除: {install['path']}")
                    shutil.rmtree(install['path'])
            except Exception as e:
                self.log(f"删除失败 {install['path']}: {str(e)}")

    def _clean_environment(self):
        """清理环境变量"""
        self.log("\n清理环境变量...")
        # 清理PATH
        for scope in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                with winreg.OpenKey(scope, 'Environment', 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
                    path, reg_type = winreg.QueryValueEx(key, 'Path')
                    new_path = ';'.join(
                        p for p in path.split(';')
                        if p and not any(kw in p.lower() for kw in ['python', 'conda'])
                    )
                    winreg.SetValueEx(key, 'Path', 0, reg_type, new_path)
                    self.log(f"已清理 {scope} 的Path变量")
            except WindowsError:
                continue

        # 删除Python特定变量
        for var in ['PYTHONPATH', 'PYTHONHOME']:
            for scope in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
                try:
                    with winreg.OpenKey(scope, 'Environment', 0, winreg.KEY_WRITE) as key:
                        winreg.DeleteValue(key, var)
                        self.log(f"已删除 {scope} 中的 {var}")
                except WindowsError:
                    continue

    def verify_uninstall(self) -> bool:
        """验证卸载是否成功"""
        self.log("\n=== 验证卸载结果 ===")
        original_installations = self.installations.copy()
        self.installations = []
        self.detect_installations()

        if not self.installations:
            self.log("所有Python安装已成功移除")
            return True

        self.log("\n以下Python安装未被完全移除:")
        for install in self.installations:
            self.log(f"- {install['type']} {install['version']} @ {install['path']}")

        self.installations = original_installations
        return False


def is_admin() -> bool:
    """检查是否以管理员身份运行"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def main():
    print("=== Python完全卸载工具 ===")
    print("开发者：罗佳煊\n")

    if not is_admin():
        print("\n请以管理员身份运行此程序！")
        print("右键点击脚本，选择'以管理员身份运行'")
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        sys.exit(1)

    uninstaller = PythonUninstaller()
    installations = uninstaller.detect_installations()

    if not installations:
        print("\n未找到任何Python安装")
        input("\n按Enter键退出...")
        return

    print("\n发现以下Python安装:")
    for i, install in enumerate(installations, 1):
        print(f"{i}. {install['type']} {install['version']} @ {install['path']} ({install['source']})")

    confirm = input("\n确定要卸载所有以上Python安装吗？(y/n): ")
    if confirm.lower() != 'y':
        print("\n操作已取消")
        input("\n按Enter键退出...")
        return

    uninstaller.uninstall()

    if not uninstaller.verify_uninstall():
        print("\n警告: 部分Python安装可能未被完全移除")
        print("建议: 手动检查上述残留并重启计算机")
    else:
        print("\n所有Python安装已成功移除")

    input("\n按Enter键退出...")


if __name__ == "__main__":
    main()