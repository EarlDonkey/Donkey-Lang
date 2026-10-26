; Donky Installer Script
#define MyAppName "Donky"
#define MyAppVersion "6.1.0"
#define MyAppPublisher "EarlDonkey"
#define MyAppURL "https://github.com/EarlDonkey/Donkey-Lang"
#define MyAppExeName "donky.exe"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
AppId={{D0A7C6B4-9B1E-4A3A-9C8B-1E2D3F4A5B6C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
; Require admin rights to install to Program Files
PrivilegesRequired=admin
OutputDir=installer_output
OutputBaseFilename=Donky-v6.1.0-Setup
SetupIconFile=donky.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "addtopath"; Description: "Add Donky to system PATH"; GroupDescription: "Other:"; Flags: checkedonce

[Files]
; Grabs the entire dist\donky folder
Source: "dist\donky\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}\Donky Compiler"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\donky.ico"
Name: "{autoprograms}\{#MyAppName}\Donky Self-Hosted Compiler"; Filename: "{app}\donkyc.bat"; IconFilename: "{app}\donky.ico"
Name: "{autoprograms}\{#MyAppName}\Donky Guestbook Server"; Filename: "{app}\examples\guestbook.donk"; IconFilename: "{app}\donky.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\donky.ico"; Tasks: desktopicon

[Registry]
; Associate .donk files with Donky
Root: HKA; Subkey: "Software\Classes\.donk"; ValueType: string; ValueName: ""; ValueData: "DonkyFile"; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\DonkyFile"; ValueType: string; ValueName: ""; ValueData: "Donky Source File"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\DonkyFile\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\donky.ico"
Root: HKA; Subkey: "Software\Classes\DonkyFile\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\donky.exe"" ""%1"""

; Add to PATH if the task is checked
Root: HKA; Subkey: "System\CurrentControlSet\Control\Session Manager\Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}"; Tasks: addtopath; Check: NeedsAddPath(ExpandConstant('{app}'))

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
function NeedsAddPath(Param: string): boolean;
var
  OrigPath: string;
begin
  if not RegQueryStringValue(HKEY_LOCAL_MACHINE,
    'SYSTEM\CurrentControlSet\Control\Session Manager\Environment',
    'Path', OrigPath)
  then begin
    Result := True;
    exit;
  end;  
  // Look for the path with leading and trailing semicolon.
  // Pos() returns 0 if not found.
  Result := Pos(';' + Param + ';', ';' + OrigPath + ';') = 0;
end;
