import os
import re
import shutil
import winreg
import subprocess
import sys
import ctypes
import glob
from typing import List, Dict, Union, Tuple

class SystemCleaner:
    def __init__(self):
        self.verbose = True
        self.is_admin = self._check_admin()
    
    def log(self, message: str) -> None:
        """记录日志信息"""
        if self.verbose:
            print(message)
    
    def _check_admin(self) -> bool:
        """检查是否以管理员身份运行"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
    
    def _ensure_admin(self) -> None:
        """确保以管理员身份运行"""
        if not self.is_admin:
            self.log("\n请以管理员身份运行此程序！")
            self.log("右键点击脚本，选择'以管理员身份运行'")
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, " ".join(sys.argv), None, 1
            )
            sys.exit(1)

class PythonUninstaller(SystemCleaner):
    def __init__(self):
        super().__init__()
        self.installations = []
        # Python特有的安装路径模式
        self.patterns = [
            (r'C:\\Python[0-9]+', "官方安装"),
            (r'C:\\Program Files\\Python[0-9]+', "Program Files安装"),
            (r'%USERPROFILE%\\AppData\\Local\\Programs\\Python', "用户目录安装"),
            (r'.*conda.*', "Conda环境"),
            (r'.*virtualenv.*', "虚拟环境")
        ]

    def detect_installations(self) -> List[Dict[str, str]]:
        """检测所有Python安装"""
        self._check_standard_installs()
        self._check_registry()
        self._check_environment_paths()
        self._check_virtualenvs()
        return self.installations

    def _check_standard_installs(self) -> None:
        """检查标准安装路径"""
        for pattern, desc in self.patterns:
            expanded = os.path.expandvars(pattern)
            for path in glob.glob(expanded):
                if os.path.exists(path):
                    self._validate_python_path(path, desc)

    def _validate_python_path(self, path: str, source: str) -> None:
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

    def _check_registry(self) -> None:
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

    def _check_environment_paths(self) -> None:
        """检查环境变量中的Python"""
        self.log("\n检查环境变量中的Python...")
        path_var = os.environ.get('PATH', '')
        for path in path_var.split(';'):
            if path and ('python' in path.lower() or 'conda' in path.lower()):
                self._validate_python_path(path, 'PATH环境变量')

    def _check_virtualenvs(self) -> None:
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

    def uninstall(self) -> None:
        """执行卸载操作"""
        if not self.installations:
            self.log("\n没有可卸载的Python安装")
            return

        self.log("\n=== 开始卸载Python ===")
        self._run_uninstallers()
        self._remove_installation_dirs()
        self._clean_environment()
        self.log("\n=== Python卸载完成 ===")

    def _run_uninstallers(self) -> None:
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
        
        # 标准路径列表
        standard_paths = [
            ("C:\\Program Files\\Java", "Oracle JRE/JDK"),
            ("C:\\Program Files (x86)\\Java", "32位Oracle JRE/JDK"), 
            ("C:\\JDK*", "自定义JDK"),
            ("C:\\Program Files\\Eclipse Foundation", "Eclipse Temurin"),
            ("C:\\Program Files\\Microsoft\\jdk*", "Microsoft JDK"),
            ("C:\\Program Files\\AdoptOpenJDK", "AdoptOpenJDK"),
            (os.path.expandvars("%USERPROFILE%\\scoop\\apps\\openjdk"), "Scoop安装")
        ]

        for path_spec in standard_paths:
            if isinstance(path_spec, tuple):
                path, desc = path_spec
            else:
                path = path_spec
                desc = "自动检测路径"
            
            if "*" in path:
                for match in glob.glob(path):
                    if os.path.exists(match):
                        self._check_java_path(match, desc)
            elif os.path.exists(path):
                self._check_java_path(path, desc)

        # 检查环境变量PATH中的Java
        self._check_path_environment()
        
        # 检查注册表中的安装
        self._check_registry_installs()

        return self.java_installations

    def _check_path_environment(self) -> None:
        """检查环境变量PATH中的Java"""
        self.log("\n检查环境变量PATH中的Java...")
        path_dirs = os.environ.get("PATH", "").split(";")
        for path in path_dirs:
            if path and ("java" in path.lower() or "jdk" in path.lower() or "jre" in path.lower()):
                self._check_java_path(path, "PATH环境变量中的Java")

    def _check_java_path(self, path: str, source: str) -> None:
        """检查指定路径是否包含Java安装"""
        # 标准化路径
        path = os.path.normpath(path)
        
        # 如果是bin目录，向上找一级
        if os.path.basename(path).lower() == "bin":
            path = os.path.dirname(path)
        
        # 检查是否已经记录过这个安装
        for install in self.java_installations:
            if os.path.normpath(install["path"]) == path:
                return

        # 查找java.exe/javac.exe
        java_exe = os.path.join(path, "bin", "java.exe")
        javac_exe = os.path.join(path, "bin", "javac.exe")
        
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
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=5
            )
            version_line = result.stderr.splitlines()[0]
            match = re.search(r'["\']?(\d+(?:\.\d+)+)[_"\']?', version_line)
            return match.group(1) if match else "未知版本"
        except Exception as e:
            self.log(f"获取版本失败 {java_exe}: {str(e)}")
            return "未知版本"

    def _check_registry_installs(self) -> None:
        """检查注册表中的Java安装"""
        self.log("\n检查注册表中的Java安装...")
        reg_paths = [
            ("SOFTWARE\\JavaSoft", "Oracle Java"),
            ("SOFTWARE\\Eclipse Foundation", "Eclipse Temurin"),
            ("SOFTWARE\\Microsoft\\JDK", "Microsoft JDK"),
            ("SOFTWARE\\AdoptOpenJDK", "AdoptOpenJDK"),
            ("SOFTWARE\\WOW6432Node\\JavaSoft", "32位Oracle Java")
        ]

        for path, vendor in reg_paths:
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path) as key:
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        subkey_name = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, subkey_name) as subkey:
                            try:
                                java_home = winreg.QueryValueEx(subkey, "JavaHome")[0]
                                self._check_java_path(java_home, f"注册表({vendor})")
                            except WindowsError:
                                pass
            except WindowsError:
                pass

    def uninstall_java(self) -> None:
        """卸载所有检测到的Java安装"""
        if not self.java_installations:
            self.log("\n未找到Java安装")
            return

        self.log("\n=== 开始卸载Java ===")
        
        self._run_wmic_uninstall()
        self._remove_java_dirs()
        self._clean_environment()
        
        self.log("\n=== Java卸载完成 ===")

    def _run_wmic_uninstall(self) -> None:
        """使用WMIC卸载Java程序"""
        self.log("\n正在通过WMIC卸载Java...")
        try:
            subprocess.run(
                'wmic product where "name like \'%Java%\'" call uninstall /nointeractive',
                shell=True,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30
            )
            self.log("WMIC卸载命令执行完成")
        except subprocess.TimeoutExpired:
            self.log("WMIC卸载超时，可能正在等待其他安装程序")
        except subprocess.CalledProcessError as e:
            self.log(f"WMIC卸载失败: {e.stderr.decode('gbk', errors='ignore').strip()}")

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

    def _clean_environment(self) -> None:
        """清理Java环境变量"""
        self.log("\n正在清理环境变量...")
        
        # 删除JAVA_HOME/JRE_HOME
        for scope in [winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE]:
            try:
                with winreg.OpenKey(scope, "Environment", 0, winreg.KEY_WRITE) as key:
                    for var in ["JAVA_HOME", "JRE_HOME"]:
                        try:
                            winreg.DeleteValue(key, var)
                            self.log(f"已删除{scope}中的{var}")
                        except WindowsError:
                            pass
            except WindowsError:
                pass
        
        # 清理Path中的Java条目
        for scope in [winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE]:
            try:
                with winreg.OpenKey(scope, "Environment", 0, winreg.KEY_READ) as key:
                    path_value, _ = winreg.QueryValueEx(key, "Path")
                
                new_path = ";".join(
                    p for p in path_value.split(";") 
                    if p and not any(kw in p.lower() for kw in ["java", "jdk", "jre"])
                )
                
                with winreg.OpenKey(scope, "Environment", 0, winreg.KEY_SET_VALUE) as key:
                    winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)
                    self.log(f"已清理{scope}的Path变量")
            except WindowsError:
                pass

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
    print("=== 开发环境完全卸载工具 ===")
    print("开发者：罗佳煊\n")
    
    while True:
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

def handle_python_uninstall():
    """处理Python卸载流程"""
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