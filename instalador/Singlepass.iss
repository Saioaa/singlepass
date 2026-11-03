; Instalador de Singlepass (Inno Setup 6)
; Antes: PyInstaller con Singlepass.spec (crea ..\dist\Singlepass).
; Compilar este fichero en Inno Setup: Build -> Compile (Ctrl+F9).
; El instalador queda en ..\instalador_salida.
;
; Que hace:
;   - copia la carpeta de PyInstaller (exe + _internal con los recursos) a
;     C:\Program Files\Materialight\Singlepass
;   - accesos directos: menu Inicio, escritorio (opcional) y arranque con
;     Windows para todos los usuarios (opcional, marcado por defecto)
;   - los datos del usuario (<usuario>\MATERIALIGHT: ajustes.json, RIPOutput,
;     Logging) los crea la app y no se tocan ni al instalar ni al desinstalar
;   - al actualizar, borra la carpeta _internal anterior para no mezclar versiones

#define NombreApp "Singlepass"
#define VersionApp "1.0.0"
#define Empresa "Materialight S.L."
#define Ejecutable "Singlepass.exe"
#define CarpetaDist "..\dist\Singlepass"

[Setup]
; AppId identifica la app para actualizar y desinstalar: no cambiarlo entre versiones
AppId={{7C2A9B64-3D1E-4F0A-9C58-5E2B1A7D9F31}
AppName={#NombreApp}
AppVersion={#VersionApp}
AppPublisher={#Empresa}
DefaultDirName={autopf}\Materialight\{#NombreApp}
DefaultGroupName=Materialight
DisableProgramGroupPage=yes
OutputDir=..\instalador_salida
OutputBaseFilename={#NombreApp}_instalador_{#VersionApp}
SetupIconFile=..\recursos\imagenes\M_02.ico
UninstallDisplayIcon={app}\{#Ejecutable}
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; si la app esta abierta al instalar una version nueva, la cierra
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "escritorio"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"
Name: "arranque"; Description: "Abrir {#NombreApp} al iniciar Windows (todos los usuarios)"; GroupDescription: "Arranque:"

[Files]
; toda la carpeta de PyInstaller, recursos incluidos (dentro de _internal)
Source: "{#CarpetaDist}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[InstallDelete]
; al actualizar, nada de una version anterior se queda mezclado
Type: filesandordirs; Name: "{app}\_internal"

[Icons]
Name: "{group}\{#NombreApp}"; Filename: "{app}\{#Ejecutable}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#NombreApp}"; Filename: "{app}\{#Ejecutable}"; WorkingDir: "{app}"; Tasks: escritorio
Name: "{commonstartup}\{#NombreApp}"; Filename: "{app}\{#Ejecutable}"; WorkingDir: "{app}"; Tasks: arranque

[Run]
Filename: "{app}\{#Ejecutable}"; Description: "Abrir {#NombreApp}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
