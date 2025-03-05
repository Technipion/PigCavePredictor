import platform
import PyInstaller.__main__


generic_options = [
    "--onefile",
]


platform_dependend_options = []


match platform.system():
    case "Linux":
        platform_dependend_options = []
    case "Windows":
        platform_dependend_options = [
            "--noconsole"
        ]


PyInstaller.__main__.run(
        ["pig_cave_predictor.py"]
        + generic_options
        + platform_dependend_options
)
