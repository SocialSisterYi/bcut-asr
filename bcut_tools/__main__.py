import logging
import sys
from argparse import ArgumentParser, FileType

from bcut_tools.cmds.asr import asr_cmd
from bcut_tools.cmds.tts import tts_cmd, available_voices_cmd

logging.basicConfig(
    format="%(asctime)s - [%(levelname)s] %(message)s",
    level=logging.INFO,
)

INFILE_FMT = ["flac", "aac", "m4a", "mp3", "wav"]
OUTFILE_FMT = ["srt", "json", "lrc", "txt"]


def build_parsers():
    parser = ArgumentParser(
        prog="bcut-tools",
        description="必剪命令行工具",
    )
    subparsers = parser.add_subparsers(dest="command")

    asr_parser = subparsers.add_parser(
        "asr",
        help="语音识别",
        description="必剪语音识别\n",
        epilog=f"支持输入音频格式: {', '.join(INFILE_FMT)}  支持自动调用ffmpeg提取视频伴音",
    )

    asr_parser.add_argument(
        "-f",
        "--format",
        nargs="?",
        default="srt",
        choices=OUTFILE_FMT,
        help="输出字幕格式",
    )
    asr_parser.add_argument(
        "-i",
        "--interval",
        nargs="?",
        type=float,
        default="1.0",
        metavar="1.0",
        help="任务状态轮询间隔(秒)",
    )
    asr_parser.add_argument("input", type=FileType("rb"), help="输入媒体文件")
    asr_parser.add_argument(
        "output",
        nargs="?",
        type=FileType("w", encoding="utf8"),
        help="输出字幕文件, 可stdout",
    )
    asr_parser.set_defaults(func=asr_cmd)


    tts_parser = subparsers.add_parser(
        "tts",
        help="语音合成",
        description="必剪语音合成",
        epilog="支持输出音频格式: wav",
    )
    
    group = tts_parser.add_mutually_exclusive_group(required=True)

    group.add_argument(
        "-l", "--list", "--available-voices",
        action="store_true",
        help="显示可用的声音列表"
    )

    group.add_argument(
        "text",
        type=str,
        nargs="?",
        help="合成文本内容"
    )

    tts_parser.add_argument(
        "-o", "--output", nargs="?", type=FileType("w"), help="输出音频文件"
    )

    tts_parser.add_argument(
        "--meta-output",
        nargs="?",
        type=FileType("w", encoding="utf-8"),
        help="输出元数据文件",
    )

    tts_parser.add_argument(
        "--sep-output",
        nargs="?",
        type=FileType("w", encoding="utf-8"),
        help="输出分割数据文件",
    )

    tts_parser.add_argument(
        "-i",
        "--interval",
        nargs="?",
        type=float,
        default="1.0",
        metavar="1.0",
        help="任务状态轮询间隔(秒)",
    )

    tts_parser.add_argument(
        "--pitch-rate", nargs="?", type=int, default=0, metavar="0", help="音调"
    )

    tts_parser.add_argument(
        "--speech-rate", nargs="?", type=int, default=0, help="语速"
    )

    tts_parser.add_argument(
        "--sample-rate", nargs="?", type=int, default=24000, help="采样率"
    )

    tts_parser.add_argument("--volume", nargs="?", type=int, default=50, help="音量")

    tts_parser.add_argument(
        "--voice",
        nargs="?",
        type=str,
        help="使用 bcut-tools tts avail",
        default="dingzhen",
    )

    tts_parser.add_argument(
        "--voice-engine", nargs="?", type=str, help="引擎类型", default="bili-fewshot"
    )

    tts_parser.set_defaults(func=tts_cmd)

    return parser


def main():
    parser = build_parsers()
    args = parser.parse_args()

    if args.command == "tts":
        if args.list:
            available_voices_cmd(args)
        else:
            tts_cmd(args)
    elif args.command == "asr":
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    sys.exit(main())
