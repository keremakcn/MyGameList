"""Audit native Android libraries, including Chaquopy's nested asset archives.

Exit code 2 denotes native 16 KB findings. --report-only exports findings without
claiming compatibility; runtime device tests remain necessary in either case.
"""
import argparse
import io
import json
from pathlib import Path
import struct
from zipfile import ZipFile, is_zipfile

def inspect_package(path):
    libraries=[]
    def scan(source,prefix=''):
        with ZipFile(source) as archive:
            if archive.testzip() is not None:raise ValueError('Corrupt package archive')
            for info in archive.infolist():
                name=prefix+info.filename
                if info.filename.endswith('.so'):
                    data=archive.read(info)
                    if data[:6]!=b'\x7fELF\x02\x01':raise ValueError('Expected a little-endian 64-bit ELF: '+name)
                    offset=struct.unpack_from('<Q',data,32)[0]
                    size,count=struct.unpack_from('<HH',data,54)
                    loads=[];findings=[]
                    for index in range(count):
                        type_,flags,fileoffset,address,physical,filesize,memsize,align=struct.unpack_from('<IIQQQQQQ',data,offset+index*size)
                        if type_==1:
                            loads.append(align)
                            if align<16384 or fileoffset%16384!=address%16384:
                                findings.append({'kind':'PT_LOAD','alignment':align})
                        if type_==0x6474e552 and (address+memsize)%16384:
                            findings.append({'kind':'PT_GNU_RELRO','end_remainder':(address+memsize)%16384})
                    libraries.append({'name':name,'load_alignment':min(loads),'findings':findings})
                elif info.filename.endswith(('.imy','.zip')):
                    data=archive.read(info)
                    if is_zipfile(io.BytesIO(data)):scan(io.BytesIO(data),name+'!/')
    scan(path)
    return {'package':path.name,'native_library_count':len(libraries),
            'libraries_with_findings':sum(bool(row['findings']) for row in libraries),'libraries':libraries}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('packages',nargs='+',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--report-only',action='store_true')
    args=parser.parse_args()
    reports=[inspect_package(path) for path in args.packages]
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(reports,indent=2),encoding='utf-8')
    for report in reports:
        print(f"{report['package']}: {report['native_library_count']} native libraries; {report['libraries_with_findings']} strict alignment findings.")
    if any(report['libraries_with_findings'] for report in reports):
        print('Native runtime review required. This report does not certify full 16 KB device compatibility.')
        return 0 if args.report_only else 2
    print('Static native alignment checks passed; runtime device validation is still required.')
    return 0

if __name__=='__main__':raise SystemExit(main())
