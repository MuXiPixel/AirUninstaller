#!/usr/bin/env python3
# AirUninstallerForLinux
# 开发者：罗佳煊
# Python 3.13.3
# 2025.8.6 / 13:38
# 1.0

import os
import re
import shutil
import subprocess
import sys
import glob
from typing import List, Dict, Union, Tuple

class SystemCleaner:
    def __init__(self):
        self.verbose = True
        self.is_root = self._check_root()
    
    def log(self, message: str) -> None:
        """记录日志信息"""
        if self.verbose:
            print(message)
    
    def clear_screen(self) -> None:
        """清屏"""
        os.system('clear')
    
    def _check_root(self) -> bool:
        """检查是否以root身份运行"""
        return os.getuid() == 0
    
    def _ensure_root(self) -> None:
        """确保以root身份运行"""
        if not self.is_root:
            self.log("\n请使用sudo或以root身份运行此程序！")
            self.log("建议命令: sudo python3 " + " ".join(sys.argv))
            sys.exit(1)

class PythonUninstaller(SystemCleaner):
    def __init__(self):
        super().__init__()
        self.installations = []
        # Linux下Python常见安装路径
        self.patterns = [
            ('/usr/bin/python*', "系统Python"),
            ('/usr/local/bin/python*', "用户编译安装Python"),
            ('/opt/python*', "自定义安装Python"),
            ('/home/*/.local/bin/python*', "用户本地Python"),
            ('/home/*/.pyenv/*', "pyenv环境"),
            ('/home/*/.virtualenvs/*', "虚拟环境"),
            ('/home/*/anaconda*', "Anaconda"),
            ('/home/*/miniconda*', "Miniconda")
        ]

    def detect_installations(self) -> List[Dict[str, str]]:
        """检测所有Python安装"""
        self._check_standard_installs()
        self._check_virtualenvs()
        self._check_conda_envs()
        return self.installations

    def _check_standard_installs(self) -> None:
        """检查标准安装路径"""
        for pattern, desc in self.patterns:
            for path in glob.glob(pattern):
                if os.path.exists(path):
                    self._validate_python_path(path, desc)

    def _validate_python_path(self, path: str, source: str) -> None:
        """验证是否为有效的Python安装"""
        # 如果是符号链接，获取真实路径
        if os.path.islink(path):
            path = os.path.realpath(path)
        
        # 如果是可执行文件
        if os.path.isfile(path) and os.access(path, os.X_OK):
            version = self._get_python_version(path)
            install_type = self._determine_install_type(path)
            
            if not any(install['path'] == path for install in self.installations):
                self.installations.append({
                    'path': path,
                    'version': version,
                    'type': install_type,
                    'source': source,
                    'executable': path
                })
                self.log(f"发现: {install_type} {version} @ {path} ({source})")
        
        # 如果是目录
        elif os.path.isdir(path):
            python_bin = os.path.join(path, 'bin', 'python')
            if os.path.exists(python_bin):
                version = self._get_python_version(python_bin)
                install_type = self._determine_install_type(path)
                
                if not any(install['path'] == path for install in self.installations):
                    self.installations.append({
                        'path': path,
                        'version': version,
                        'type': install_type,
                        'source': source,
                        'executable': python_bin
                    })
                    self.log(f"发现: {install_type} {version} @ {path} ({source})")

    def _get_python_version(self, python_path: str) -> str:
        """获取Python版本"""
        try:
            result = subprocess.run(
                [python_path, '--version'],
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
        if '.local' in path_lower or '.pyenv' in path_lower:
            return '用户安装'
        if '/usr/bin' in path_lower:
            return '系统Python'
        return '自定义安装'

    def _check_virtualenvs(self) -> None:
        """检测虚拟环境"""
        self.log("\n扫描虚拟环境...")
        search_paths = [
            os.path.expanduser('~'),
            '/opt',
            '/usr/local'
        ]

        for search_path in search_paths:
            for root, dirs, _ in os.walk(search_path):
                if 'pyvenv.cfg' in dirs or 'bin/python' in dirs:
                    self._validate_python_path(root, '虚拟环境')
                for dir_name in dirs:
                    if dir_name.lower() in ('venv', 'virtualenv', '.venv'):
                        self._validate_python_path(os.path.join(root, dir_name), '虚拟环境')

    def _check_conda_envs(self) -> None:
        """检测Conda环境"""
        self.log("\n扫描Conda环境...")
        conda_paths = [
            os.path.expanduser('~/anaconda3'),
            os.path.expanduser('~/miniconda3'),
            '/opt/anaconda3',
            '/opt/miniconda3'
        ]

        for conda_path in conda_paths:
            if os.path.exists(conda_path):
                self._validate_python_path(conda_path, 'Conda')
                envs_path = os.path.join(conda_path, 'envs')
                if os.path.exists(envs_path):
                    for env in os.listdir(envs_path):
                        self._validate_python_path(os.path.join(envs_path, env), 'Conda环境')

    def uninstall(self) -> None:
        """执行卸载操作"""
        if not self.installations:
            self.log("\n没有可卸载的Python安装")
            return

        self.log("\n=== 开始卸载Python ===")
        self._remove_installation_files()
        self._clean_environment()
        self.log("\n=== Python卸载完成 ===")

    def _remove_installation_files(self) -> None:
        """删除Python安装文件"""
        self.log("\n删除Python安装文件...")
        for install in self.installations:
            path = install['path']
            
            # 如果是系统Python，提示不要删除
            if install['type'] == '系统Python':
                self.log(f"警告: 跳过系统Python {path} - 请使用系统包管理器卸载")
                continue
            
            try:
                if os.path.isfile(path):
                    os.remove(path)
                    self.log(f"已删除文件: {path}")
                elif os.path.isdir(path):
                    shutil.rmtree(path)
                    self.log(f"已删除目录: {path}")
            except Exception as e:
                self.log(f"删除失败 {path}: {str(e)}")

    def _clean_environment(self) -> None:
        """清理环境变量"""
        self.log("\n清理Python环境变量...")
        # 获取当前用户的环境文件
        env_files = [
            os.path.expanduser('~/.bashrc'),
            os.path.expanduser('~/.bash_profile'),
            os.path.expanduser('~/.zshrc'),
            os.path.expanduser('~/.profile'),
            '/etc/environment'
        ]

        for env_file in env_files:
            if os.path.exists(env_file):
                try:
                    # 备份原文件
                    shutil.copy2(env_file, env_file + '.bak')
                    
                    # 读取内容并过滤Python相关环境变量
                    with open(env_file, 'r') as f:
                        lines = f.readlines()
                    
                    new_lines = []
                    for line in lines:
                        if not any(keyword in line for keyword in ['PYTHON', 'CONDA', 'ANACONDA']):
                            new_lines.append(line)
                    
                    # 写入新内容
                    with open(env_file, 'w') as f:
                        f.writelines(new_lines)
                    
                    self.log(f"已清理环境文件: {env_file}")
                except Exception as e:
                    self.log(f"清理环境文件失败 {env_file}: {str(e)}")

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
        # Linux下Java常见安装路径
        self.java_patterns = [
            ('/usr/lib/jvm/*', "系统Java"),
            ('/usr/java/*', "Oracle Java"),
            ('/opt/jdk*', "自定义JDK"),
            ('/opt/java*', "自定义Java"),
            ('/home/*/.sdkman/candidates/java/*', "SDKMAN安装"),
            ('/home/*/.local/share/umake/java/*', "Ubuntu Make安装")
        ]

    def find_java_installations(self) -> List[Dict[str, str]]:
        """检测所有Java安装"""
        self._check_standard_installs()
        self._check_alternatives()
        self._check_environment_paths()
        return self.java_installations

    def _check_standard_installs(self) -> None:
        """检查标准安装路径"""
        for pattern, desc in self.java_patterns:
            for path in glob.glob(pattern):
                if os.path.exists(path):
                    self._validate_java_path(path, desc)

    def _validate_java_path(self, path: str, source: str) -> None:
        """验证是否为有效的Java安装"""
        # 如果是目录
        if os.path.isdir(path):
            java_bin = os.path.join(path, 'bin', 'java')
            if os.path.exists(java_bin):
                version = self._get_java_version(java_bin)
                install_type = "JDK" if os.path.exists(os.path.join(path, 'bin', 'javac')) else "JRE"
                
                if not any(install['path'] == path for install in self.java_installations):
                    self.java_installations.append({
                        'path': path,
                        'version': version,
                        'source': source,
                        'type': install_type
                    })
                    self.log(f"发现: {install_type} {version} @ {path} ({source})")

    def _get_java_version(self, java_path: str) -> str:
        """获取Java版本"""
        try:
            result = subprocess.run(
                [java_path, '-version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            version_line = result.stderr.splitlines()[0]
            match = re.search(r'["\']?(\d+(?:\.\d+)+)[_"\']?', version_line)
            return match.group(1) if match else "未知版本"
        except Exception as e:
            self.log(f"获取版本失败 {java_path}: {str(e)}")
            return "未知版本"

    def _check_alternatives(self) -> None:
        """检查alternatives系统中的Java"""
        self.log("\n检查alternatives系统中的Java...")
        try:
            result = subprocess.run(
                ['update-alternatives', '--list', 'java'],
                capture_output=True,
                text=True
            )
            for path in result.stdout.splitlines():
                if path:
                    java_dir = os.path.dirname(os.path.dirname(path))
                    self._validate_java_path(java_dir, 'alternatives系统')
        except Exception as e:
            self.log(f"检查alternatives失败: {str(e)}")

    def _check_environment_paths(self) -> None:
        """检查环境变量中的Java"""
        self.log("\n检查环境变量中的Java...")
        path_dirs = os.environ.get('PATH', '').split(':')
        for path in path_dirs:
            if path and ('java' in path.lower() or 'jdk' in path.lower() or 'jre' in path.lower()):
                java_bin = os.path.join(path, 'java')
                if os.path.exists(java_bin):
                    java_dir = os.path.dirname(os.path.dirname(java_bin))
                    self._validate_java_path(java_dir, 'PATH环境变量')

    def uninstall_java(self) -> None:
        """卸载所有检测到的Java安装"""
        if not self.java_installations:
            self.log("\n未找到Java安装")
            return

        self.log("\n=== 开始卸载Java ===")
        self._remove_java_files()
        self._clean_environment()
        self._remove_alternatives()
        self.log("\n=== Java卸载完成 ===")

    def _remove_java_files(self) -> None:
        """删除Java安装文件"""
        self.log("\n删除Java安装文件...")
        for install in self.java_installations:
            path = install['path']
            
            # 如果是系统Java，提示不要删除
            if install['source'] == '系统Java':
                self.log(f"警告: 跳过系统Java {path} - 请使用系统包管理器卸载")
                continue
            
            try:
                if os.path.exists(path):
                    shutil.rmtree(path)
                    self.log(f"已删除: {path}")
            except Exception as e:
                self.log(f"删除失败 {path}: {str(e)}")

    def _clean_environment(self) -> None:
        """清理Java环境变量"""
        self.log("\n清理Java环境变量...")
        env_files = [
            os.path.expanduser('~/.bashrc'),
            os.path.expanduser('~/.bash_profile'),
            os.path.expanduser('~/.zshrc'),
            os.path.expanduser('~/.profile'),
            '/etc/environment'
        ]

        for env_file in env_files:
            if os.path.exists(env_file):
                try:
                    # 备份原文件
                    shutil.copy2(env_file, env_file + '.bak')
                    
                    # 读取内容并过滤Java相关环境变量
                    with open(env_file, 'r') as f:
                        lines = f.readlines()
                    
                    new_lines = []
                    for line in lines:
                        if not any(keyword in line.lower() for keyword in ['java', 'jdk', 'jre']):
                            new_lines.append(line)
                    
                    # 写入新内容
                    with open(env_file, 'w') as f:
                        f.writelines(new_lines)
                    
                    self.log(f"已清理环境文件: {env_file}")
                except Exception as e:
                    self.log(f"清理环境文件失败 {env_file}: {str(e)}")

    def _remove_alternatives(self) -> None:
        """从alternatives系统中移除Java"""
        self.log("\n从alternatives系统中移除Java...")
        try:
            # 获取所有Java相关的alternatives
            result = subprocess.run(
                ['update-alternatives', '--list', 'java'],
                capture_output=True,
                text=True
            )
            
            for java_path in result.stdout.splitlines():
                if java_path:
                    # 从alternatives中移除
                    subprocess.run(
                        ['update-alternatives', '--remove', 'java', java_path],
                        check=True
                    )
                    self.log(f"已从alternatives中移除: {java_path}")
        except Exception as e:
            self.log(f"更新alternatives失败: {str(e)}")

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
        print("=== Linux开发环境完全卸载工具 ===")
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
    
    if not uninstaller.is_root:
        uninstaller._ensure_root()
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
        print("建议: 手动检查上述残留并重启终端")
    else:
        print("\n所有Python安装已成功移除")
    
    input("\n按Enter键返回主菜单...")

def handle_java_uninstall():
    """处理Java卸载流程"""
    cleaner = SystemCleaner()
    cleaner.clear_screen()
    print("\n=== Java卸载 ===")
    uninstaller = JavaUninstaller()
    
    if not uninstaller.is_root:
        uninstaller._ensure_root()
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
        print("建议: 手动检查上述残留并重启终端")
    else:
        print("\n所有Java安装已成功移除")
    
    input("\n按Enter键返回主菜单...")

if __name__ == "__main__":
    main_menu()