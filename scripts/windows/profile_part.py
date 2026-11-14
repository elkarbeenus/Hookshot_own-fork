"""(LaküenRecomp) The play profile's part for the Windows setup list, made the same, byte for byte, wherever it runs: the
work/ files (hookshot_pieces.prof, hot_funcs.txt, hot_order.txt, image/chunks.txt: addresses and counts, no game code) of a
Linux share part this repository published while upstream's profile was still downloaded, stored (no compression) with fixed
times under HookshotBuilder/tools/work/.

    python -I scripts/windows/profile_part.py <linux share part .zip> <out .zip>
"""
import sys
import zipfile


def main(src, out):
    with zipfile.ZipFile(src) as s:
        names = sorted(i.filename for i in s.infolist() if i.filename.startswith("work/") and not i.is_dir())
        if "work/hookshot_pieces.prof" not in names:
            sys.exit("%s holds no work/hookshot_pieces.prof" % src)
        with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED) as z:
            for n in names:
                info = zipfile.ZipInfo("HookshotBuilder/tools/" + n, date_time=(1980, 1, 1, 0, 0, 0))
                info.external_attr = 0o644 << 16
                z.writestr(info, s.read(n))
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))
