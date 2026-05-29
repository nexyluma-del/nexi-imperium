<#
AUFGABE 011b - Display-Farben fuer Daily/SDR zuruecksetzen

Macht nur reversible lokale Display-Aktionen:
- HDR / Advanced Color fuer aktive Displays ausschalten
- GPU-Gamma-Ramp auf neutral/linear setzen
- Windows Color Filter deaktivieren, falls vorhanden

Keine Treiber-Deinstallation, keine Monitor-OSD-Aenderung, keine Spielsettings.
#>

[CmdletBinding()]
param(
    [string]$BackupDir = "C:\Users\nexil\Desktop\KI\display-backup"
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null

$source = @"
using System;
using System.Runtime.InteropServices;

public static class DisplayColorNative
{
    private const uint QDC_ONLY_ACTIVE_PATHS = 0x00000002;

    [StructLayout(LayoutKind.Sequential)]
    public struct LUID
    {
        public uint LowPart;
        public int HighPart;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct DISPLAYCONFIG_RATIONAL
    {
        public uint Numerator;
        public uint Denominator;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct DISPLAYCONFIG_PATH_SOURCE_INFO
    {
        public LUID adapterId;
        public uint id;
        public uint modeInfoIdx;
        public uint statusFlags;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct DISPLAYCONFIG_PATH_TARGET_INFO
    {
        public LUID adapterId;
        public uint id;
        public uint modeInfoIdx;
        public uint outputTechnology;
        public uint rotation;
        public uint scaling;
        public DISPLAYCONFIG_RATIONAL refreshRate;
        public uint scanLineOrdering;
        public int targetAvailable;
        public uint statusFlags;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct DISPLAYCONFIG_PATH_INFO
    {
        public DISPLAYCONFIG_PATH_SOURCE_INFO sourceInfo;
        public DISPLAYCONFIG_PATH_TARGET_INFO targetInfo;
        public uint flags;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct DISPLAYCONFIG_DEVICE_INFO_HEADER
    {
        public uint type;
        public uint size;
        public LUID adapterId;
        public uint id;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct DISPLAYCONFIG_GET_ADVANCED_COLOR_INFO
    {
        public DISPLAYCONFIG_DEVICE_INFO_HEADER header;
        public uint value;
        public uint colorEncoding;
        public uint bitsPerColorChannel;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct DISPLAYCONFIG_SET_ADVANCED_COLOR_STATE
    {
        public DISPLAYCONFIG_DEVICE_INFO_HEADER header;
        public uint value;
    }

    [DllImport("user32.dll")]
    private static extern int GetDisplayConfigBufferSizes(uint flags, out uint numPathArrayElements, out uint numModeInfoArrayElements);

    [DllImport("user32.dll")]
    private static extern int QueryDisplayConfig(
        uint flags,
        ref uint numPathArrayElements,
        [Out] DISPLAYCONFIG_PATH_INFO[] pathInfoArray,
        ref uint numModeInfoArrayElements,
        IntPtr modeInfoArray,
        IntPtr currentTopologyId);

    [DllImport("user32.dll")]
    private static extern int DisplayConfigGetDeviceInfo(ref DISPLAYCONFIG_GET_ADVANCED_COLOR_INFO requestPacket);

    [DllImport("user32.dll")]
    private static extern int DisplayConfigSetDeviceInfo(ref DISPLAYCONFIG_SET_ADVANCED_COLOR_STATE requestPacket);

    [DllImport("gdi32.dll")]
    private static extern IntPtr CreateDC(string lpszDriver, string lpszDevice, string lpszOutput, IntPtr lpInitData);

    [DllImport("gdi32.dll")]
    private static extern bool DeleteDC(IntPtr hdc);

    [DllImport("gdi32.dll")]
    private static extern bool SetDeviceGammaRamp(IntPtr hdc, ref GammaRamp ramp);

    [StructLayout(LayoutKind.Sequential)]
    public struct GammaRamp
    {
        [MarshalAs(UnmanagedType.ByValArray, SizeConst = 256)]
        public ushort[] Red;
        [MarshalAs(UnmanagedType.ByValArray, SizeConst = 256)]
        public ushort[] Green;
        [MarshalAs(UnmanagedType.ByValArray, SizeConst = 256)]
        public ushort[] Blue;
    }

    public static string DisableAdvancedColor()
    {
        uint pathCount;
        uint modeCount;
        int result = GetDisplayConfigBufferSizes(QDC_ONLY_ACTIVE_PATHS, out pathCount, out modeCount);
        if (result != 0)
        {
            return "GetDisplayConfigBufferSizes failed: " + result;
        }

        var paths = new DISPLAYCONFIG_PATH_INFO[pathCount];
        IntPtr modes = Marshal.AllocHGlobal((int)Math.Max(1, modeCount) * 256);
        try
        {
            result = QueryDisplayConfig(QDC_ONLY_ACTIVE_PATHS, ref pathCount, paths, ref modeCount, modes, IntPtr.Zero);
            if (result != 0)
            {
                return "QueryDisplayConfig failed: " + result;
            }

            string output = "";
            for (int i = 0; i < pathCount; i++)
            {
                var target = paths[i].targetInfo;
                var getInfo = new DISPLAYCONFIG_GET_ADVANCED_COLOR_INFO();
                getInfo.header.type = 9; // DISPLAYCONFIG_DEVICE_INFO_GET_ADVANCED_COLOR_INFO
                getInfo.header.size = (uint)Marshal.SizeOf(typeof(DISPLAYCONFIG_GET_ADVANCED_COLOR_INFO));
                getInfo.header.adapterId = target.adapterId;
                getInfo.header.id = target.id;

                result = DisplayConfigGetDeviceInfo(ref getInfo);
                if (result != 0)
                {
                    output += "Target " + i + ": AdvancedColor query failed: " + result + Environment.NewLine;
                    continue;
                }

                bool supported = (getInfo.value & 0x1) != 0;
                bool enabled = (getInfo.value & 0x2) != 0;
                output += "Target " + i + ": supported=" + supported + " enabled_before=" + enabled + " bits=" + getInfo.bitsPerColorChannel + Environment.NewLine;

                if (supported && enabled)
                {
                    var setInfo = new DISPLAYCONFIG_SET_ADVANCED_COLOR_STATE();
                    setInfo.header.type = 10; // DISPLAYCONFIG_DEVICE_INFO_SET_ADVANCED_COLOR_STATE
                    setInfo.header.size = (uint)Marshal.SizeOf(typeof(DISPLAYCONFIG_SET_ADVANCED_COLOR_STATE));
                    setInfo.header.adapterId = target.adapterId;
                    setInfo.header.id = target.id;
                    setInfo.value = 0; // disable HDR / advanced color
                    result = DisplayConfigSetDeviceInfo(ref setInfo);
                    output += "Target " + i + ": disable_result=" + result + Environment.NewLine;
                }
            }
            return output.TrimEnd();
        }
        finally
        {
            Marshal.FreeHGlobal(modes);
        }
    }

    public static bool ResetGammaRamp()
    {
        var ramp = new GammaRamp
        {
            Red = new ushort[256],
            Green = new ushort[256],
            Blue = new ushort[256]
        };
        for (int i = 0; i < 256; i++)
        {
            ushort value = (ushort)Math.Min(65535, i * 257);
            ramp.Red[i] = value;
            ramp.Green[i] = value;
            ramp.Blue[i] = value;
        }

        IntPtr hdc = CreateDC("DISPLAY", null, null, IntPtr.Zero);
        if (hdc == IntPtr.Zero)
        {
            return false;
        }
        try
        {
            return SetDeviceGammaRamp(hdc, ref ramp);
        }
        finally
        {
            DeleteDC(hdc);
        }
    }
}
"@

Add-Type -TypeDefinition $source -Language CSharp

$timestamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$logPath = Join-Path $BackupDir "display-color-reset-$timestamp.log"

"Display color reset started: $(Get-Date)" | Tee-Object -FilePath $logPath

"Step: Disable HDR / Advanced Color" | Tee-Object -FilePath $logPath -Append
[DisplayColorNative]::DisableAdvancedColor() | Tee-Object -FilePath $logPath -Append

"Step: Reset GPU gamma ramp to neutral" | Tee-Object -FilePath $logPath -Append
"Gamma reset result: $([DisplayColorNative]::ResetGammaRamp())" | Tee-Object -FilePath $logPath -Append

"Step: Disable Windows Color Filters if key exists" | Tee-Object -FilePath $logPath -Append
$colorFilterKey = "HKCU:\Software\Microsoft\ColorFiltering"
if (Test-Path -LiteralPath $colorFilterKey) {
    Set-ItemProperty -LiteralPath $colorFilterKey -Name "Active" -Type DWord -Value 0 -ErrorAction SilentlyContinue
    Set-ItemProperty -LiteralPath $colorFilterKey -Name "FilterType" -Type DWord -Value 0 -ErrorAction SilentlyContinue
    "ColorFiltering Active=0 FilterType=0" | Tee-Object -FilePath $logPath -Append
}
else {
    "ColorFiltering key not present" | Tee-Object -FilePath $logPath -Append
}

"Display color reset finished: $(Get-Date)" | Tee-Object -FilePath $logPath -Append
Write-Host "Display-Farbreset abgeschlossen. Log: $logPath"

