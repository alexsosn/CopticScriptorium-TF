"""Corpus-wide PAULA package and semantic-shape audit."""
from __future__ import annotations
import argparse, json, zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterator
import xml.etree.ElementTree as ET

XML_BASE="{http://www.w3.org/XML/1998/namespace}base"
CONTENT_KINDS={"body","markList","featList","multiFeatList","structList","relList"}

def _local_name(tag): return tag.rsplit("}",1)[-1]
def _ordered(counter): return {k:counter[k] for k in sorted(counter)}

def _dataset_for_archive(root, path):
    rel=path.relative_to(root); p=rel.parts
    if len(p)==2 and p[1].endswith("_PAULA.zip"): return f"{p[0]}/{p[1][:-10]}",rel.as_posix()
    if len(p)==3 and p[1].endswith("_PAULA") and p[2].endswith("_PAULA.zip"): return f"{p[0]}/{p[1][:-6]}",rel.as_posix()
    raise ValueError(f"unsupported PAULA archive location: {rel.as_posix()}")

def _dataset_for_directory(root,path):
    rel=path.relative_to(root); p=rel.parts
    if len(p)!=2 or not p[1].endswith("_PAULA"): raise ValueError(f"unsupported PAULA directory location: {rel.as_posix()}")
    return f"{p[0]}/{p[1][:-6]}",rel.as_posix()

def _packages(root):
    packages=[]; archives=sorted(root.rglob("*_PAULA.zip"),key=lambda p:p.as_posix()); parents={p.parent.resolve() for p in archives}
    for p in archives:
        d,s=_dataset_for_archive(root,p); packages.append({"dataset":d,"source":s,"packaging":"archive","path":p})
    for p in sorted((x for x in root.rglob("*_PAULA") if x.is_dir()),key=lambda p:p.as_posix()):
        if p.resolve() in parents: continue
        d,s=_dataset_for_directory(root,p); packages.append({"dataset":d,"source":s,"packaging":"directory","path":p})
    idx={}
    for p in packages:
        if p["dataset"] in idx: raise ValueError(f"duplicate PAULA package representation for {p['dataset']}")
        idx[p["dataset"]]=p
    return [idx[k] for k in sorted(idx)]

def _archive_members(package):
    with zipfile.ZipFile(package["path"]) as a:
        for m in sorted(a.namelist()):
            if not m.endswith("/") and m.lower().endswith(".xml"): yield f"{package['source']}!/{m}",a.read(m)

def _all_archive_names(package):
    with zipfile.ZipFile(package["path"]) as a: return sorted(m for m in a.namelist() if not m.endswith("/"))

def _directory_members(root,package):
    for m in sorted(package["path"].rglob("*.xml"),key=lambda p:p.as_posix()): yield m.relative_to(root).as_posix(),m.read_bytes()

def _all_directory_names(root,package):
    return sorted(p.relative_to(package["path"]).as_posix() for p in package["path"].rglob("*") if p.is_file())

def _content_element(root):
    c=[x for x in root if _local_name(x.tag) in CONTENT_KINDS]
    if len(c)!=1: raise ValueError("expected exactly one PAULA content element")
    return c[0]

def _header_id(root):
    for c in root:
        if _local_name(c.tag)=="header": return c.attrib.get("paula_id")
    return None

def _feature_values(c): return [x.attrib["value"] for x in c if _local_name(x.tag)=="feat" and "value" in x.attrib]
def _multi_feature_values(c):
    out=defaultdict(list)
    for mf in c:
        if _local_name(mf.tag)!="multiFeat": continue
        for f in mf:
            if _local_name(f.tag)=="feat" and f.attrib.get("name") and "value" in f.attrib: out[f.attrib["name"]].append(f.attrib["value"])
    return {k:out[k] for k in sorted(out)}
def _is_metadata_base(base):
    if not base: return False
    b=base.strip(); return b=="meta" or Path(b).name.endswith(".anno.xml")

def audit_upstream(root: Path|str)->dict[str,Any]:
    root=Path(root); packages=_packages(root); packaging=Counter(); kinds=Counter(); list_types=defaultdict(Counter); metadata_types=Counter(); metadata=[]; examples=defaultdict(list); errors=[]; no_xml=[]; xml_count=0; parsed=0
    for package in packages:
        packaging[package["packaging"]]+=1
        try:
            members=list(_archive_members(package)) if package["packaging"]=="archive" else list(_directory_members(root,package))
        except (OSError,zipfile.BadZipFile) as e:
            errors.append({"kind":"unreadable_package","source":package["source"],"detail":str(e)}); continue
        parsed+=1
        if not members:
            names=_all_archive_names(package) if package["packaging"]=="archive" else _all_directory_names(root,package)
            no_xml.append({"dataset":package["dataset"],"source":package["source"],"members":names[:100]})
            errors.append({"kind":"unsupported_package_shape","source":package["source"],"detail":"no PAULA XML members"}); continue
        for source,raw in members:
            xml_count+=1
            try: r=ET.fromstring(raw)
            except (ET.ParseError,UnicodeDecodeError) as e:
                errors.append({"kind":"malformed_xml","source":source,"detail":str(e)}); continue
            if _local_name(r.tag)!="paula": errors.append({"kind":"invalid_root","source":source,"detail":_local_name(r.tag)}); continue
            try: c=_content_element(r)
            except ValueError as e: errors.append({"kind":"invalid_content","source":source,"detail":str(e)}); continue
            kind=_local_name(c.tag); kinds[kind]+=1; typ=c.attrib.get("type"); base=c.attrib.get(XML_BASE) or c.attrib.get("xml:base"); pid=_header_id(r)
            if kind!="body" and typ: list_types[kind][typ]+=1
            if kind=="featList" and typ and len(examples[typ])<3:
                examples[typ].append({"dataset":package["dataset"],"source":source,"paula_id":pid,"base":base,"values":_feature_values(c)[:5]})
            if kind=="featList" and _is_metadata_base(base) and typ and typ!="annoFeat":
                metadata_types[typ]+=1; metadata.append({"dataset":package["dataset"],"source":source,"paula_id":pid,"base":base,"type":typ,"values":_feature_values(c)})
            elif kind=="multiFeatList" and _is_metadata_base(base):
                for t,vals in _multi_feature_values(c).items():
                    metadata_types[t]+=1; metadata.append({"dataset":package["dataset"],"source":source,"paula_id":pid,"base":base,"type":t,"values":vals})
    return {"source_package_count":len(packages),"parsed_package_count":parsed,"datasets":[p["dataset"] for p in packages],"packaging":_ordered(packaging),"xml_member_count":xml_count,"element_kind_counts":_ordered(kinds),"list_type_occurrences":{k:_ordered(list_types[k]) for k in sorted(list_types)},"feature_type_examples":{k:examples[k] for k in sorted(examples)},"metadata_feature_type_occurrences":_ordered(metadata_types),"metadata_feature_instances":sorted(metadata,key=lambda x:(x["dataset"],x["source"],x["type"])),"packages_without_xml_members":sorted(no_xml,key=lambda x:x["dataset"]),"errors":sorted(errors,key=lambda x:(x.get("source",""),x.get("kind",""),x.get("detail","")))}

def render_report_json(report): return json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+"\n"
def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("upstream",type=Path); p.add_argument("--output",type=Path); a=p.parse_args(argv); s=render_report_json(audit_upstream(a.upstream))
    if a.output: a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(s,encoding="utf-8")
    else: print(s,end="")
    return 0
if __name__=="__main__": raise SystemExit(main())
