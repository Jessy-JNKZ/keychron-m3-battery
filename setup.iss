[Setup]
AppName=Keychron M3 Battery Monitor
AppVersion=2.0
DefaultDirName={pf}\Keychron
DefaultGroupName=Keychron
OutputDir=.
OutputBaseFilename=KeychronBatterySetup
Compression=lzma
SolidCompression=yes
PrivilegesRequired=admin

[Files]
Source: "keychron_battery_jj.pyw"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "config.json"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{group}\Keychron M3 Battery"; Filename: "pythonw.exe"; Parameters: """{app}\keychron_battery_jj.pyw"""; WorkingDir: "{app}"
Name: "{group}\Documentation (README)"; Filename: "{app}\README.md"
Name: "{group}\Désinstaller Keychron Battery"; Filename: "{uninstallexe}"

[Code]
var
  StartupPage: TInputOptionWizardPage;
  RunPage: TOutputMsgWizardPage;
  RunAfterInstallCheckbox: TCheckBox;

procedure InitializeWizard();
begin
  StartupPage := CreateInputOptionPage(wpSelectDir,
    'Configuration du démarrage', 'Préférences de lancement',
    'Voulez-vous que Keychron Battery Monitor se lance automatiquement au démarrage de Windows ?',
    False, False);
  StartupPage.Add('Lancer l''application automatiquement au démarrage de Windows');
  StartupPage.Values[0] := True;

  RunPage := CreateOutputMsgPage(wpFinished,
    'Fin de l''installation', 'Prêt à utiliser Keychron Battery Monitor',
    'L''installation s''est terminée avec succès.');
  
  RunAfterInstallCheckbox := TCheckBox.Create(RunPage);
  RunAfterInstallCheckbox.Parent := RunPage.Surface;
  RunAfterInstallCheckbox.Left := 0;
  RunAfterInstallCheckbox.Top := 40;
  RunAfterInstallCheckbox.Width := 400;
  RunAfterInstallCheckbox.Caption := 'Lancer Keychron M3 Battery Monitor dès maintenant';
  RunAfterInstallCheckbox.Checked := True;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  StartupFolder: String;
  ShortcutPath: String;
  WshShell: Variant;
  Shortcut: Variant;
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    StartupFolder := ExpandConstant('{userstartup}');
    ShortcutPath := StartupFolder + '\KeychronBatteryMonitorJJ.lnk';

    if StartupPage.Values[0] then
    begin
      try
        WshShell := CreateOleObject('WScript.Shell');
        Shortcut := WshShell.CreateShortcut(ShortcutPath);
        Shortcut.TargetPath := 'pythonw.exe';
        Shortcut.Arguments := '"' + ExpandConstant('{app}\keychron_battery_jj.pyw') + '"';
        Shortcut.WorkingDirectory := ExpandConstant('{app}');
        Shortcut.Save();
      except
      end;
    end
    else
    begin
      if FileExists(ShortcutPath) then
        DeleteFile(ShortcutPath);
    end;

    if RunAfterInstallCheckbox.Checked then
    begin
      Exec('pythonw.exe', '"' + ExpandConstant('{app}\keychron_battery_jj.pyw') + '"', '', SW_HIDE, ewNoWait, ResultCode);
    end;
  end;
end;