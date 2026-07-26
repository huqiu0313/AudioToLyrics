; AudioToLyrics 安装包（Inno Setup 6）
; 构建：ISCC /DAppVersion=<version> packaging/installer.iss
; 版本号未传入时回退默认值（与 config.VERSION 保持一致）

#ifndef AppVersion
  #define AppVersion "4.0"
#endif

[Setup]
AppName=AudioToLyrics
AppVersion={#AppVersion}
AppPublisher=huqiu0313
DefaultDirName={autopf}\AudioToLyrics
DefaultGroupName=AudioToLyrics
OutputDir={#SourcePath}
OutputBaseFilename=AudioToLyrics-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallMode=x64compatible
PrivilegesRequired=admin
WizardStyle=modern

; 注：安装界面为英文（Inno 官方发行版不含简体中文语言包）

[Files]
Source: "..\dist\AudioToLyrics\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\AudioToLyrics"; Filename: "{app}\AudioToLyrics.exe"
Name: "{group}\卸载 AudioToLyrics"; Filename: "{uninstallexe}"
Name: "{autodesktop}\AudioToLyrics"; Filename: "{app}\AudioToLyrics.exe"

[Run]
Filename: "{app}\AudioToLyrics.exe"; Flags: postinstall skipifsilent nowait
