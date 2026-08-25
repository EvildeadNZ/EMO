Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$product = "Evil's Media Encoding Platform"
$installDir = Join-Path $env:LOCALAPPDATA "EvilsMediaEncodingPlatform"
$sourceDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$form = New-Object System.Windows.Forms.Form
$form.Text = "$product - Platform Builder"
$form.Size = New-Object System.Drawing.Size(620,430)
$form.StartPosition = 'CenterScreen'
$form.BackColor = [System.Drawing.Color]::FromArgb(8,8,12)
$form.ForeColor = [System.Drawing.Color]::White
$form.FormBorderStyle = 'FixedDialog'
$form.MaximizeBox = $false

$title = New-Object System.Windows.Forms.Label
$title.Text = "EVIL'S MEDIA ENCODING PLATFORM"
$title.Font = New-Object System.Drawing.Font('Segoe UI',18,[System.Drawing.FontStyle]::Bold)
$title.ForeColor = [System.Drawing.Color]::FromArgb(211,92,255)
$title.Location = New-Object System.Drawing.Point(28,28)
$title.AutoSize = $true
$form.Controls.Add($title)

$sub = New-Object System.Windows.Forms.Label
$sub.Text = "Platform 5.0 Preview * Powered by EMO`r`nThis bootstrap installs the preview, then the guided Platform Builder configures HandBrake, storage, workflow and media server settings."
$sub.Font = New-Object System.Drawing.Font('Segoe UI',10)
$sub.Location = New-Object System.Drawing.Point(31,72)
$sub.Size = New-Object System.Drawing.Size(540,62)
$form.Controls.Add($sub)

$status = New-Object System.Windows.Forms.Label
$status.Text = "Ready to build your platform."
$status.Font = New-Object System.Drawing.Font('Segoe UI',10,[System.Drawing.FontStyle]::Bold)
$status.Location = New-Object System.Drawing.Point(31,158)
$status.Size = New-Object System.Drawing.Size(540,50)
$form.Controls.Add($status)

$progress = New-Object System.Windows.Forms.ProgressBar
$progress.Location = New-Object System.Drawing.Point(32,218)
$progress.Size = New-Object System.Drawing.Size(536,22)
$progress.Minimum = 0
$progress.Maximum = 100
$form.Controls.Add($progress)

$desktop = New-Object System.Windows.Forms.CheckBox
$desktop.Text = "Create desktop shortcut"
$desktop.Checked = $true
$desktop.Location = New-Object System.Drawing.Point(32,260)
$desktop.AutoSize = $true
$desktop.BackColor = $form.BackColor
$desktop.ForeColor = $form.ForeColor
$form.Controls.Add($desktop)

$install = New-Object System.Windows.Forms.Button
$install.Text = "BUILD MY PLATFORM"
$install.Font = New-Object System.Drawing.Font('Segoe UI',10,[System.Drawing.FontStyle]::Bold)
$install.Location = New-Object System.Drawing.Point(350,315)
$install.Size = New-Object System.Drawing.Size(218,42)
$install.BackColor = [System.Drawing.Color]::FromArgb(112,33,143)
$install.ForeColor = [System.Drawing.Color]::White
$install.FlatStyle = 'Flat'
$form.Controls.Add($install)

$install.Add_Click({
    $install.Enabled = $false
    try {
        $status.Text = "Checking Python runtime..."
        $progress.Value = 10
        [System.Windows.Forms.Application]::DoEvents()
        $python = Get-Command python -ErrorAction SilentlyContinue
        if (-not $python) { $python = Get-Command py -ErrorAction SilentlyContinue }
        if (-not $python) {
            [System.Windows.Forms.MessageBox]::Show("This preview build needs Python 3.11+ because it is not frozen into a standalone EXE yet.`r`n`r`nThe production EMP installer will bundle its runtime.", $product, 'OK', 'Warning') | Out-Null
            Start-Process "https://www.python.org/downloads/windows/"
            $status.Text = "Python is required for this preview."
            return
        }
        $pyExe = $python.Source
        $pyArgs = @()
        if ($python.Name -eq 'py.exe') { $pyArgs = @('-3') }

        # Use the windowed Python executable for shortcuts and normal GUI launch.
        $guiExe = $pyExe
        if ($python.Name -eq 'py.exe') {
            $candidate = Join-Path (Split-Path -Parent $pyExe) 'pyw.exe'
            if (Test-Path $candidate) { $guiExe = $candidate }
        } elseif ($python.Name -eq 'python.exe') {
            $candidate = Join-Path (Split-Path -Parent $pyExe) 'pythonw.exe'
            if (Test-Path $candidate) { $guiExe = $candidate }
        }

        $status.Text = "Installing EMP application files..."
        $progress.Value = 30
        [System.Windows.Forms.Application]::DoEvents()
        New-Item -ItemType Directory -Force -Path $installDir | Out-Null
        Get-ChildItem -LiteralPath $sourceDir -Force | Where-Object { $_.Name -notin @('EMP Preview Installer.ps1','INSTALL EMP 5 PREVIEW.bat') } | ForEach-Object {
            Copy-Item -LiteralPath $_.FullName -Destination $installDir -Recurse -Force
        }

        $status.Text = "Preparing EMP interface runtime..."
        $progress.Value = 50
        [System.Windows.Forms.Application]::DoEvents()
        $req = Join-Path $installDir 'requirements.txt'
        $args = $pyArgs + @('-m','pip','install','-q','-r',$req)
        $proc = Start-Process -FilePath $pyExe -ArgumentList $args -Wait -PassThru -WindowStyle Hidden
        if ($proc.ExitCode -ne 0) { throw "Python requirements could not be installed (exit $($proc.ExitCode))." }

        $status.Text = "Creating shortcuts..."
        $progress.Value = 78
        [System.Windows.Forms.Application]::DoEvents()
        $shell = New-Object -ComObject WScript.Shell
        $startDir = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'
        $shortcutPath = Join-Path $startDir "Evil's Media Encoding Platform.lnk"
        $sc = $shell.CreateShortcut($shortcutPath)
        $sc.TargetPath = $guiExe
        $runArgs = $pyArgs + @((Join-Path $installDir 'EvilsMediaOptimizer.pyw'))
        $sc.Arguments = ($runArgs | ForEach-Object { '"' + $_ + '"' }) -join ' '
        $sc.WorkingDirectory = $installDir
        $ico = Join-Path $installDir 'assets\evils_skull.ico'
        if (Test-Path $ico) { $sc.IconLocation = $ico }
        $sc.Save()
        if ($desktop.Checked) {
            $d = $shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) "Evil's Media Encoding Platform.lnk"))
            $d.TargetPath = $sc.TargetPath; $d.Arguments = $sc.Arguments; $d.WorkingDirectory = $installDir
            if (Test-Path $ico) { $d.IconLocation = $ico }
            $d.Save()
        }

        $status.Text = "EMP installed successfully."
        $progress.Value = 100
        [System.Windows.Forms.Application]::DoEvents()

        # Keep the completion message in front of the installer and do not launch
        # the Platform Builder until the user acknowledges it.
        $form.TopMost = $true
        $form.Activate()
        [System.Windows.Forms.MessageBox]::Show($form, "EMP is installed. The Platform Builder will now guide you through HandBrake, workflow, locations and media-server setup.", $product, 'OK', 'Information') | Out-Null
        $form.TopMost = $false

        $status.Text = "Launching Platform Builder..."
        [System.Windows.Forms.Application]::DoEvents()
        $launchArgs = $pyArgs + @((Join-Path $installDir 'EvilsMediaOptimizer.pyw'))
        Start-Process -FilePath $guiExe -ArgumentList $launchArgs -WorkingDirectory $installDir
        $form.Close()
    } catch {
        $status.Text = "Installation stopped: $($_.Exception.Message)"
        [System.Windows.Forms.MessageBox]::Show($_.Exception.Message, "$product - Installer", 'OK', 'Error') | Out-Null
    } finally {
        $install.Enabled = $true
    }
})

[void]$form.ShowDialog()
