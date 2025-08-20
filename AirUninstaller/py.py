import winreg
import ctypes
import sys

def is_admin():
    """检查是否以管理员权限运行"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def delete_edge_registry_keys():
    """删除Edge相关的注册表项"""
    edge_keys = [
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Edge"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Edge"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Edge"),
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\EdgeUpdate"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\EdgeUpdate"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate")
    ]
    
    deleted_keys = 0
    
    for hive, key_path in edge_keys:
        try:
            with winreg.OpenKey(hive, key_path, 0, winreg.KEY_ALL_ACCESS) as key:
                # 先删除子项
                i = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        winreg.DeleteKey(key, subkey_name)
                        print(f"已删除: {key_path}\\{subkey_name}")
                        deleted_keys += 1
                    except OSError:
                        break
                    i += 1
                
                # 关闭当前键以便删除父键
                winreg.CloseKey(key)
                
                # 尝试删除父键
                try:
                    winreg.DeleteKey(hive, key_path)
                    print(f"已删除: {key_path}")
                    deleted_keys += 1
                except WindowsError as e:
                    print(f"无法删除 {key_path}: {e}")
        except WindowsError as e:
            print(f"无法打开 {key_path}: {e}")
    
    return deleted_keys

def main():
    if not is_admin():
        print("请以管理员身份运行此脚本！")
        input("按任意键退出...")
        sys.exit(1)
    
    print("警告：此操作将删除Edge浏览器的注册表项，可能导致Edge重置或需要重新安装。")
    confirm = input("确定要继续吗？(y/n): ").lower()
    
    if confirm != 'y':
        print("操作已取消。")
        return
    
    print("开始删除Edge注册表项...")
    deleted = delete_edge_registry_keys()
    print(f"操作完成，共删除 {deleted} 个注册表项。")
    
    if deleted > 0:
        print("建议重启计算机以使更改生效。")

if __name__ == "__main__":
    main()