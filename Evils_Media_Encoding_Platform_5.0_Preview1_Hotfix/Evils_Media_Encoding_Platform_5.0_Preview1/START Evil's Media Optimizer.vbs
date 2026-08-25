Option Explicit

Dim shell, fso, folder, command
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
folder = fso.GetParentFolderName(WScript.ScriptFullName)

command = "pythonw.exe """ & folder & "\EvilsMediaOptimizer.pyw"""
shell.Run command, 0, False
