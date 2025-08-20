import os
import re
import shutil
import winreg
import subprocess
import sys
import ctypes
import glob
from typing import List, Dict, Union

class JavaUninstaller:
    def __init__(self):
        self.java_installations = []
        self.verbose = True

    def log(self, message: str) -> None:
        if self.verbose:
            print(message)

    def find_java_installations(self) -> List[Dict[str, str]]:
        """自动检测系统中所有Java安装"""
        self.log("\n=== 正在扫描Java安装 ===")
        
        # 修正后的标准路径列表 (每个元素都是元组或字符串)
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
            if path and ("java" in path.lower() or "jdk" in path.lower()):
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
        
        self.log("\n=== 卸载完成 ===")

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
        self.log("\n=== 验证卸载结果 ===")
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


def is_admin() -> bool:
    """检查是否以管理员身份运行"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def main():
    print("=== Java完全卸载工具 ===")
    
    # 检查管理员权限
    if not is_admin():
        print("\n请以管理员身份运行此程序！")
        print("右键点击脚本，选择'以管理员身份运行'")
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        sys.exit(1)
    
    print("正在扫描系统中的Java安装...")
    uninstaller = JavaUninstaller()
    installations = uninstaller.find_java_installations()
    
    if not installations:
        print("\n未找到任何Java安装")
        return
    
    print("\n发现以下Java安装:")
    for i, install in enumerate(installations, 1):
        print(f"{i}. {install['type']} {install['version']} @ {install['path']} ({install['source']})")
    
    confirm = input("\n确定要卸载所有以上Java安装吗？(y/n): ")
    if confirm.lower() != 'y':
        print("\n操作已取消")
        return
    
    uninstaller.uninstall_java()
    if not uninstaller.verify_uninstall():
        print("\n警告: 部分Java安装可能未被完全移除")
        print("建议: 手动检查上述残留并重启计算机")
    else:
        print("\n所有Java安装已成功移除")
    
    input("\n按Enter键退出...")

if __name__ == "__main__":
    print("开发者：罗佳煊\n")
    main()