"""Prepare one supplied formal task without importing or running scientific workers."""
import argparse
from pathlib import Path
from release_support import prepare
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--family',required=True);p.add_argument('--id',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();print(prepare(a.family,a.id,a.output))
if __name__=='__main__':main()
