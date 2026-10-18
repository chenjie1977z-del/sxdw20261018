"""Re-export already generated art. Requires ImageMagick and Pillow for validation."""
from pathlib import Path
import argparse,concurrent.futures,hashlib,json,os,subprocess
from PIL import Image

ROOT=Path(__file__).resolve().parent
ICC=Path('/usr/share/color/icc/sRGB.icc')
def command(args):
    environment=os.environ.copy();environment['XDG_CACHE_HOME']='/tmp/anatomy-font-cache'
    Path(environment['XDG_CACHE_HOME']).mkdir(parents=True,exist_ok=True)
    subprocess.run(['magick',*map(str,args)],check=True,env=environment)

def compose(sex):
    command([*[ROOT/'sources'/f'{sex}-{v}.png' for v in ['front','side','back']],'+append','+repage','-background','white','-gravity','north','-splice','0x80','-gravity','northwest','-font','DejaVu-Sans','-pointsize','28','-fill','#203b3c','-annotate','+441+22','ANTERIOR','-annotate','+1474+22','LATERAL','-annotate','+2484+22','POSTERIOR','-alpha','remove','-alpha','off',ROOT/'native'/f'{sex}-three-views.png'])

def export(job):
    name,source=job
    common=['-background','white','-alpha','remove','-alpha','off','-depth','8','-profile',ICC,'-units','PixelsPerInch','-density','600']
    command([source,*common,'-compress','LZW',ROOT/'native'/f'{name}-native-600dpi.tif'])
    command([source,'-filter','Lanczos','-resize','9449x6544','-background','white','-gravity','center','-extent','9921x7016',*common,ROOT/'A3-600dpi'/f'{name}-A3-600dpi.png'])
    print('Exported',name,flush=True)

def validate():
    report={'a3_mm':[420,297],'output_dpi':600,'a3_is_resampled':True,'files':[]}
    for folder,pattern,resampled in [('A3-600dpi','*.png',True),('native','*.tif',False)]:
        for p in sorted((ROOT/folder).glob(pattern)):
            with Image.open(p) as image:
                image.load()
                if resampled:assert image.size==(9921,7016),(p,image.size)
                assert image.mode=='RGB',(p,image.mode)
                assert all(abs(float(v)-600)<.02 for v in image.info['dpi'])
                assert image.info.get('icc_profile'),p
                entry={'file':str(p.relative_to(ROOT)),'pixels':list(image.size),'dpi':[float(v) for v in image.info['dpi']],'resampled':resampled,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
                if not resampled:entry['native_print_mm_at_600']=[round(v/600*25.4,2) for v in image.size]
                report['files'].append(entry)
    assert len(report['files'])==12
    (ROOT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Verified all 12 RGB/ICC/600-DPI files',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--views-only',action='store_true');parser.add_argument('--validate-only',action='store_true');args=parser.parse_args()
    if not args.validate_only:
        jobs=[]
        for sex in ['male','female']:
            compose(sex);jobs.append((f'{sex}-three-views',ROOT/'native'/f'{sex}-three-views.png'))
            if not args.views_only:
                jobs.extend((f'{sex}-{region}-detail',ROOT/'sources'/f'{sex}-{region}-detail.png') for region in ['upper','lower'])
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(export,jobs))
    validate()
