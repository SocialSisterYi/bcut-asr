#!/bin/python3
from setuptools import setup

setup(
    name='bcut-asr',
    version='0.0.2',
    description='使用必剪API的语音字幕识别',
    author='SocialSisterYi',
    author_email='1440239038@qq.com',
    url='https://github.com/SocialSisterYi/bcut-asr',
    packages=['bcut_asr'],
    license=open('LICENSE', 'r', encoding='utf8').read(),
    install_requires=[
        'requests>=2.28.1',
        'pydantic>=1.9.0',
        'ffmpeg_python>=0.2.0',
    ],
    entry_points={
        'console_scripts': [
            'bcut_asr = bcut_asr.__main__:main'
        ]
    }
)
