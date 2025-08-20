#!/usr/bin/env python3
# AirUninstallerForMacOS
# 开发者：罗佳煊
# 适配MacOS版本

# ----------------
# Python 3.13.3
# 2025.8.6
# 1.0
# ----------------

import os
import re
import shutil
import subprocess
import sys
import glob
import plistlib
from typing import List, Dict, Union, Tuple

class SystemCleaner:
    def __init__(self):
        self.verbose = True
        self.is_admin = self._check_admin()
    
    def log(self, message: str) -> None:
        """记录日志信息"""
        if self.verbose:
            print(message)
    
    def clear_screen(self) -> None:
        """MacOS清屏"""
        os.system('clear')
    
    def _check_admin(self) -> bool:
        """检查是否以管理员身份运行"""
        return os.getuid() == 0
    
    def _ensure_admin(self) -> None:
        """确保以管理员身份运行"""
        if not self.is_admin:
            self.log("\n请使用sudo运行此程序！")
            self.log("请在终端中执行: sudo python3 " + " ".join(sys.argv))
            sys.exit(1)

class PythonUninstaller(SystemCleaner):
    def __init__(self):
        super().__init__()
        self.installations = []
        # MacOS特有的Python安装路径模式
        self.patterns = [
            ('/Library/Frameworks/Python.framework/Versions/*', "官方框架安装"),
            ('/usr/local/bin/python*', "Homebrew安装"),
            ('/usr/bin/python*', "系统Python"),
            ('/opt/homebrew/bin/python*', "ARM Homebrew安装"),
            ('/Users/*/.pyenv/versions/*', "pyenv安装"),
            ('/Users/*/.virtualenvs/*', "虚拟环境"),
            ('/Users/*/anaconda*', "Anaconda安装"),
            ('/Users/*/miniconda*', "Miniconda安装")
        ]

    def detect_installations(self) -> List[Dict[str, str]]:
        """检测所有Python安装"""
        self._check_standard_installs()
        self._check_homebrew()
        self._check_conda()
        self._check_virtualenvs()
        return self.installations

    def _check_standard_installs(self) -> None:
        """检查标准安装路径"""
        for pattern, desc in self.patterns:
            expanded = os.path.expanduser(pattern)
            for path in glob.glob(expanded):
                if os.path.exists(path):
                    self._validate_python_path(path, desc)

    def _validate_python_path(self, path: str, source: str) -> None:
        """验证是否为有效的Python安装"""
        # 如果是二进制文件，直接获取路径
        if os.path.isfile(path) and 'python' in os.path.basename(path):
            python_exe = path
            path = os.path.dirname(os.path.dirname(python_exe))
        else:
            python_exe = os.path.join(path, 'bin', 'python3')
            if not os.path.exists(python_exe):
                python_exe = os.path.join(path, 'bin', 'python')
        
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
                text=True
            )
            return result.stdout.strip() or result.stderr.strip()
        except Exception as e:
            return f"版本获取失败: {str(e)}"

    def _determine_install_type(self, path: str) -> str:
        """判断安装类型"""
        path_lower = path.lower()
        if 'conda' in path_lower or 'anaconda' in path_lower:
            return 'Conda'
        if 'virtualenv' in path_lower or 'venv' in path_lower or '.virtualenvs' in path_lower:
            return 'Virtualenv'
        if 'pyenv' in path_lower:
            return 'pyenv'
        if 'homebrew' in path_lower or '/usr/local/' in path_lower:
            return 'Homebrew'
        if '/Library/Frameworks/' in path_lower:
            return '官方框架'
        if '/usr/bin/' in path_lower:
            return '系统Python'
        return '自定义安装'

    def _check_homebrew(self) -> None:
        """检查Homebrew安装的Python"""
        self.log("\n检查Homebrew安装的Python...")
        try:
            brew_list = subprocess.run(
                ['brew', 'list'],
                capture_output=True,
                text=True
            )
            if 'python' in brew_list.stdout or 'python@' in brew_list.stdout:
                brew_prefix = subprocess.run(
                    ['brew', '--prefix'],
                    capture_output=True,
                    text=True
                ).stdout.strip()
                python_paths = glob.glob(f"{brew_prefix}/opt/python@*")
                for path in python_paths:
                    self._validate_python_path(path, 'Homebrew')
        except FileNotFoundError:
            self.log("Homebrew未安装")

    def _check_conda(self) -> None:
        """检查Conda安装"""
        self.log("\n检查Conda安装...")
        conda_paths = [
            os.path.expanduser('~/anaconda'),
            os.path.expanduser('~/anaconda2'),
            os.path.expanduser('~/anaconda3'),
            os.path.expanduser('~/miniconda'),
            os.path.expanduser('~/miniconda2'),
            os.path.expanduser('~/miniconda3'),
            '/opt/anaconda',
            '/opt/anaconda2',
            '/opt/anaconda3',
            '/opt/miniconda',
            '/opt/miniconda2',
            '/opt/miniconda3'
        ]
        
        for path in conda_paths:
            if os.path.exists(path):
                self._validate_python_path(path, 'Conda')

    def _check_virtualenvs(self) -> None:
        """检测虚拟环境"""
        self.log("\n扫描虚拟环境...")
        search_paths = [
            os.path.expanduser('~'),
            '/usr/local/',
            '/opt/'
        ]

        for search_path in search_paths:
            for root, dirs, _ in os.walk(search_path):
                if 'pyvenv.cfg' in dirs or 'bin/python' in dirs:
                    self._validate_python_path(root, '虚拟环境')
                # 检查常见虚拟环境目录名
                for dir_name in dirs:
                    if dir_name.lower() in ('venv', 'virtualenv', '.venv'):
                        self._validate_python_path(os.path.join(root, dir_name), '虚拟环境')

    def uninstall(self) -> None:
        """执行卸载操作"""
        if not self.installations:
            self.log("\n没有可卸载的Python安装")
            return

        self.log("\n=== 开始卸载Python ===")
        self._remove_installation_dirs()
        self._clean_environment()
        self.log("\n=== Python卸载完成 ===")

    def _remove_installation_dirs(self) -> None:
        """删除安装目录"""
        self.log("\n删除安装目录...")
        for install in self.installations:
            try:
                if os.path.exists(install['path']):
                    self.log(f"正在删除: {install['path']}")
                    shutil.rmtree(install['path'])
            except Exception as e:
                self.log(f"删除失败 {install['path']}: {str(e)}")

    def _clean_environment(self) -> None:
        """清理环境变量"""
        self.log("\n清理Python环境变量...")
        # 清理.bash_profile, .zshrc等
        shell_files = [
            os.path.expanduser('~/.bash_profile'),
            os.path.expanduser('~/.zshrc'),
            os.path.expanduser('~/.bashrc'),
            os.path.expanduser('~/.profile')
        ]
        
        for shell_file in shell_files:
            if os.path.exists(shell_file):
                try:
                    with open(shell_file, 'r') as f:
                        lines = f.readlines()
                    
                    new_lines = []
                    for line in lines:
                        if not any(kw in line.lower() for kw in ['python', 'pyenv', 'conda', 'anaconda']):
                            new_lines.append(line)
                    
                    with open(shell_file, 'w') as f:
                        f.writelines(new_lines)
                    
                    self.log(f"已清理 {shell_file} 中的Python相关环境变量")
                except Exception as e:
                    self.log(f"清理 {shell_file} 失败: {str(e)}")

    def verify_uninstall(self) -> bool:
        """验证卸载是否成功"""
        self.log("\n=== 验证Python卸载结果 ===")
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

class JavaUninstaller(SystemCleaner):
    def __init__(self):
        super().__init__()
        self.java_installations = []

    def find_java_installations(self) -> List[Dict[str, str]]:
        """自动检测系统中所有Java安装"""
        self.log("\n=== 正在扫描Java安装 ===")
        
        # MacOS标准路径列表
        standard_paths = [
            ('/Library/Java/JavaVirtualMachines/*', "Oracle JDK"),
            ('/Library/Internet Plug-Ins/JavaAppletPlugin.plugin', "JRE插件"),
            ('/usr/local/Cellar/openjdk@*', "Homebrew OpenJDK"),
            ('/opt/homebrew/Cellar/openjdk@*', "ARM Homebrew OpenJDK"),
            ('/Users/*/.sdkman/candidates/java/*', "SDKMAN安装"),
            ('/Users/*/Library/Java/JavaVirtualMachines/*', "用户目录JDK")
        ]

        for path_spec in standard_paths:
            if isinstance(path_spec, tuple):
                path, desc = path_spec
            else:
                path = path_spec
                desc = "自动检测路径"
            
            for match in glob.glob(os.path.expanduser(path)):
                if os.path.exists(match):
                    self._check_java_path(match, desc)

        # 检查环境变量PATH中的Java
        self._check_path_environment()
        
        # 检查Homebrew安装的Java
        self._check_homebrew_java()
        
        return self.java_installations

    def _check_path_environment(self) -> None:
        """检查环境变量PATH中的Java"""
        self.log("\n检查环境变量PATH中的Java...")
        path_dirs = os.environ.get("PATH", "").split(":")
        for path in path_dirs:
            if path and ("java" in path.lower() or "jdk" in path.lower() or "jre" in path.lower()):
                self._check_java_path(path, "PATH环境变量中的Java")

    def _check_java_path(self, path: str, source: str) -> None:
        """检查指定路径是否包含Java安装"""
        # 标准化路径
        path = os.path.normpath(path)
        
        # 如果是Homebrew链接，解析真实路径
        if os.path.islink(path):
            path = os.path.realpath(path)
        
        # 如果是bin目录，向上找一级
        if os.path.basename(path).lower() == "bin":
            path = os.path.dirname(path)
        
        # 检查是否已经记录过这个安装
        for install in self.java_installations:
            if os.path.normpath(install["path"]) == path:
                return

        # 查找java/javac
        java_exe = os.path.join(path, "bin", "java")
        javac_exe = os.path.join(path, "bin", "javac")
        
        if os.path.exists(java_exe):
            version = self._get_java_version(java_exe)
            install_type = "JDK" if os.path.exists(javac_exe) else "JRE"
            
            self.java_installations.append({
                "path": path,
                "version": version,
                "source": source,
                "type": install_type
            })
            self.log(f"发现: {install_type} {version} @ {path} ({source})")

    def _get_java_version(self, java_exe: str) -> str:
        """获取Java版本"""
        try:
            result = subprocess.run(
                [java_exe, "-version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            version_line = result.stderr.splitlines()[0]
            match = re.search(r'["\']?(\d+(?:\.\d+)+)[_"\']?', version_line)
            return match.group(1) if match else "未知版本"
        except Exception as e:
            self.log(f"获取版本失败 {java_exe}: {str(e)}")
            return "未知版本"

    def _check_homebrew_java(self) -> None:
        """检查Homebrew安装的Java"""
        self.log("\n检查Homebrew安装的Java...")
        try:
            brew_list = subprocess.run(
                ['brew', 'list'],
                capture_output=True,
                text=True
            )
            if 'openjdk' in brew_list.stdout or 'java' in brew_list.stdout:
                brew_prefix = subprocess.run(
                    ['brew', '--prefix'],
                    capture_output=True,
                    text=True
                ).stdout.strip()
                java_paths = glob.glob(f"{brew_prefix}/opt/openjdk@*")
                for path in java_paths:
                    self._check_java_path(path, 'Homebrew')
        except FileNotFoundError:
            self.log("Homebrew未安装")

    def uninstall_java(self) -> None:
        """卸载所有检测到的Java安装"""
        if not self.java_installations:
            self.log("\n未找到Java安装")
            return

        self.log("\n=== 开始卸载Java ===")
        
        self._remove_java_dirs()
        self._remove_java_plugins()
        self._clean_environment()
        
        self.log("\n=== Java卸载完成 ===")

    def _remove_java_dirs(self) -> None:
        """删除Java安装目录"""
        self.log("\n正在删除Java安装目录...")
        for install in self.java_installations:
            path = install["path"]
            if os.path.exists(path):
                try:
                    shutil.rmtree(path)
                    self.log(f"已删除: {path}")
                except Exception as e:
                    self.log(f"删除失败 {path}: {str(e)}")

    def _remove_java_plugins(self) -> None:
        """删除Java浏览器插件"""
        self.log("\n正在删除Java浏览器插件...")
        plugin_paths = [
            '/Library/Internet Plug-Ins/JavaAppletPlugin.plugin',
            '/Library/PreferencePanes/JavaControlPanel.prefPane'
        ]
        
        for path in plugin_paths:
            if os.path.exists(path):
                try:
                    shutil.rmtree(path)
                    self.log(f"已删除Java插件: {path}")
                except Exception as e:
                    self.log(f"删除Java插件失败 {path}: {str(e)}")

    def _clean_environment(self) -> None:
        """清理Java环境变量"""
        self.log("\n正在清理环境变量...")
        # 清理.bash_profile, .zshrc等
        shell_files = [
            os.path.expanduser('~/.bash_profile'),
            os.path.expanduser('~/.zshrc'),
            os.path.expanduser('~/.bashrc'),
            os.path.expanduser('~/.profile')
        ]
        
        for shell_file in shell_files:
            if os.path.exists(shell_file):
                try:
                    with open(shell_file, 'r') as f:
                        lines = f.readlines()
                    
                    new_lines = []
                    for line in lines:
                        if not any(kw in line.lower() for kw in ['java', 'jdk', 'jre']):
                            new_lines.append(line)
                    
                    with open(shell_file, 'w') as f:
                        f.writelines(new_lines)
                    
                    self.log(f"已清理 {shell_file} 中的Java相关环境变量")
                except Exception as e:
                    self.log(f"清理 {shell_file} 失败: {str(e)}")

    def verify_uninstall(self) -> bool:
        """验证卸载是否成功"""
        self.log("\n=== 验证Java卸载结果 ===")
        remaining = []
        original_installations = self.java_installations.copy()
        self.java_installations = []
        self.find_java_installations()
        remaining = self.java_installations
        
        if not remaining:
            self.log("所有Java安装已成功移除")
            return True
        
        self.log("以下Java安装未被完全移除:")
        for install in remaining:
            self.log(f"- {install['type']} {install['version']} @ {install['path']}")
        
        # 恢复原始安装列表
        self.java_installations = original_installations
        return False

def main_menu():
    """主菜单界面"""
    cleaner = SystemCleaner()
    
    while True:
        cleaner.clear_screen()
        print("=== MacOS开发环境完全卸载工具 ===")
        print("开发者：罗佳煊\n")
        print("\n请选择要卸载的环境:")
        print("1. Python")
        print("2. Java")
        print("3. 退出")
        
        choice = input("\n请输入选项(1-3): ")
        
        if choice == '1':
            handle_python_uninstall()
        elif choice == '2':
            handle_java_uninstall()
        elif choice == '3':
            print("\n感谢使用，再见！")
            sys.exit(0)
        else:
            print("\n无效的输入，请重新选择")
            input("按Enter键继续...")

def handle_python_uninstall():
    """处理Python卸载流程"""
    cleaner = SystemCleaner()
    cleaner.clear_screen()
    print("\n=== Python卸载 ===")
    uninstaller = PythonUninstaller()
    
    if not uninstaller.is_admin:
        uninstaller._ensure_admin()
        return
    
    installations = uninstaller.detect_installations()
    
    if not installations:
        print("\n未找到任何Python安装")
        input("\n按Enter键返回主菜单...")
        return
    
    print("\n发现以下Python安装:")
    for i, install in enumerate(installations, 1):
        print(f"{i}. {install['type']} {install['version']} @ {install['path']} ({install['source']})")
    
    confirm = input("\n确定要卸载所有以上Python安装吗？(y/n): ")
    if confirm.lower() != 'y':
        print("\n操作已取消")
        input("\n按Enter键返回主菜单...")
        return
    
    uninstaller.uninstall()
    
    if not uninstaller.verify_uninstall():
        print("\n警告: 部分Python安装可能未被完全移除")
        print("建议: 手动检查上述残留并重启计算机")
    else:
        print("\n所有Python安装已成功移除")
    
    input("\n按Enter键返回主菜单...")

def handle_java_uninstall():
    """处理Java卸载流程"""
    cleaner = SystemCleaner()
    cleaner.clear_screen()
    print("\n=== Java卸载 ===")
    uninstaller = JavaUninstaller()
    
    if not uninstaller.is_admin:
        uninstaller._ensure_admin()
        return
    
    installations = uninstaller.find_java_installations()
    
    if not installations:
        print("\n未找到任何Java安装")
        input("\n按Enter键返回主菜单...")
        return
    
    print("\n发现以下Java安装:")
    for i, install in enumerate(installations, 1):
        print(f"{i}. {install['type']} {install['version']} @ {install['path']} ({install['source']})")
    
    confirm = input("\n确定要卸载所有以上Java安装吗？(y/n): ")
    if confirm.lower() != 'y':
        print("\n操作已取消")
        input("\n按Enter键返回主菜单...")
        return
    
    uninstaller.uninstall_java()
    
    if not uninstaller.verify_uninstall():
        print("\n警告: 部分Java安装可能未被完全移除")
        print("建议: 手动检查上述残留并重启计算机")
    else:
        print("\n所有Java安装已成功移除")
    
    input("\n按Enter键返回主菜单...")

if __name__ == "__main__":
    main_menu()