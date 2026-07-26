#!/usr/bin/env python3
"""
SCP-ECG Parser for Edan SE-1200 Express
Handles Edan's specific SCP-ECG binary format with filename-based patient extraction.

Usage:
    python3 scp_parser.py <file.scp> --json
    python3 scp_parser.py <file.scp> --log
"""

import struct, json, sys, os, re
from datetime import datetime
from pathlib import Path

LEAD_NAMES = ["I","II","III","aVR","aVL","aVF","V1","V2","V3","V4","V5","V6",
               "V7","V8","V9","V3R","V4R","V5R","V6R","V7R","X","Y","Z"]

SECTION_NAMES = {
    0:"Header/Pointers",1:"Patient Demographics",2:"Huffman Tables",
    3:"Lead Definition",4:"QRS Locations",5:"Reference Beat",
    6:"Rhythm Data",7:"Global Measurements",8:"Clinical Summary",
    9:"Free Text",10:"Lead Measurements",11:"Annotations",12:"Manufacturer"
}

class EdanSCPParser:

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self.raw      = open(filepath, 'rb').read()
        self.size     = len(self.raw)
        self.sections = {}

    def parse(self) -> dict:
        # 1. Extract from filename (most reliable for Edan)
        fname_data = self._parse_filename()

        # 2. Parse SCP binary sections
        self._parse_sections()

        # 3. Extract structured data
        patient      = self._extract_patient(fname_data)
        recording    = self._extract_recording(fname_data)
        measurements = self._extract_measurements()
        leads        = self._extract_leads()
        diagnosis    = self._extract_diagnosis()
        interpretation = self._build_interpretation(measurements)

        return {
            "file": {
                "name":       self.filename,
                "size_bytes": self.size,
                "parsed_at":  datetime.utcnow().isoformat() + "Z",
                "format":     "SCP-ECG (Edan SE-1200)",
            },
            "patient":        patient,
            "recording":      recording,
            "measurements":   measurements,
            "leads":          leads,
            "diagnosis":      diagnosis,
            "interpretation": interpretation,
        }

    # ── Filename parser (Edan naming: YYYYMMDD-HHMMSS-<patient_field>.scp) ──
    def _parse_filename(self) -> dict:
        """
        Edan SE-1200 stores whatever the operator typed in the patient field
        as the last segment of the filename before .scp.
        
        Possible formats typed by operator:
          99662                -> patient_id only (pure number)
          catherine lyimo      -> patient_name only (pure name)
          john doe 12345       -> patient_name + patient_id (name then number)
          12345 john doe       -> patient_id + patient_name (number then name)
          MARY001              -> alphanumeric patient_id
        """
        result = {}
        # Strip FTP receiver prefix added by liscomecg.py: YYYYMMDD_HHMMSS_
        name = re.sub(r'^\d{8}_\d{6}_', '', self.filename)
        name = re.sub(r'\.scp$', '', name, flags=re.IGNORECASE)

        m = re.match(r'^(\d{8})-(\d{6})-(.+)$', name)
        if not m:
            return result

        date_s, time_s, patient_raw = m.groups()
        result['rec_date'] = f"{date_s[:4]}-{date_s[4:6]}-{date_s[6:]}"
        result['rec_time'] = f"{time_s[:2]}:{time_s[2:4]}:{time_s[4:]}"
        result.update(self._parse_patient_field(patient_raw.strip()))
        return result

    def _parse_patient_field(self, raw: str) -> dict:
        """Parse whatever the operator typed into the Edan machine patient field."""
        out = {}

        # Pure number -> patient_id only  e.g. "99662", "1"
        if re.match(r'^\d+$', raw):
            out['patient_id'] = raw
            return out

        # Alphanumeric no spaces -> ID  e.g. "MARY001", "PT2025"
        if re.match(r'^[A-Za-z0-9]+$', raw) and re.search(r'\d', raw):
            out['patient_id'] = raw.upper()
            return out

        # Name then number -> name + ID  e.g. "john doe 12345"
        m = re.match(r'^(.+?)\s+(\d+)\s*$', raw)
        if m:
            name_raw, id_raw = m.groups()
            out['patient_id'] = id_raw
            self._set_name(out, name_raw)
            return out

        # Number then name -> ID + name  e.g. "12345 john doe"
        m = re.match(r'^(\d+)\s+(.+)$', raw)
        if m:
            id_raw, name_raw = m.groups()
            out['patient_id'] = id_raw
            self._set_name(out, name_raw)
            return out

        # Pure name  e.g. "catherine lyimo", "anisia m petro"
        self._set_name(out, raw)
        return out

    def _set_name(self, out: dict, raw: str):
        name  = raw.strip().title()
        parts = name.split()
        out['patient_name']       = name
        out['patient_first_name'] = parts[0] if parts else None
        out['patient_last_name']  = ' '.join(parts[1:]) if len(parts) > 1 else None
    # ── SCP Binary section parser ──────────────────────────────────────────────
    def _parse_sections(self):
        """Parse SCP-ECG section pointer table and decode each section."""
        raw = self.raw
        if len(raw) < 6:
            return

        # Global header: CRC(2) + length(4) = 6 bytes, then pointer table
        # Each pointer: section_id(2) + length(4) + byte_offset(4) = 10 bytes
        offset = 6
        pointers = []
        while offset + 10 <= min(len(raw), 6 + 20 * 10):
            sec_id  = struct.unpack_from('<H', raw, offset)[0]
            length  = struct.unpack_from('<I', raw, offset + 2)[0]
            idx     = struct.unpack_from('<I', raw, offset + 6)[0]
            offset += 10
            if sec_id == 0 and length == 0 and idx == 0:
                break
            if 0 < length < self.size and 0 < idx < self.size:
                pointers.append((sec_id, length, idx))

        for sec_id, length, idx in pointers:
            data = raw[idx: idx + length]
            if len(data) < 16:
                continue
            # Section header: CRC(2) + ID(2) + length(4) + version(1) + protocol(1) + reserved(6)
            payload = data[16:]
            self.sections[sec_id] = {
                'id': sec_id, 'name': SECTION_NAMES.get(sec_id, f'Sec{sec_id}'),
                'length': length, 'data': data, 'payload': payload,
            }

        # If no sections found via pointer table, try to scan for SCP section headers
        if not self.sections:
            self._scan_sections_fallback()

    def _scan_sections_fallback(self):
        """Scan raw bytes for SCP section signatures."""
        raw = self.raw
        for offset in range(0, min(len(raw) - 16, 2048), 2):
            sec_id = struct.unpack_from('<H', raw, offset + 2)[0]
            length = struct.unpack_from('<I', raw, offset + 4)[0]
            if sec_id <= 12 and 16 < length < self.size - offset:
                payload = raw[offset + 16: offset + length]
                if sec_id not in self.sections:
                    self.sections[sec_id] = {
                        'id': sec_id, 'name': SECTION_NAMES.get(sec_id, f'Sec{sec_id}'),
                        'length': length, 'payload': payload,
                    }

    def _get_payload(self, sec_id: int) -> bytes:
        return self.sections.get(sec_id, {}).get('payload', b'')

    # ── Section 1: Patient demographics ───────────────────────────────────────
    def _decode_section1(self) -> dict:
        payload = self._get_payload(1)
        if not payload:
            return {}
        demo   = {}
        offset = 0
        TAG_MAP = {
            2:  'last_name',  3: 'first_name', 4: 'patient_id',
            5:  'second_name',6: 'age',         7: 'dob',
            8:  'height',    9: 'weight',      10: 'sex',
            14: 'rec_date', 15: 'rec_time',    16: 'device',
            17: 'room',     19: 'technician',  20: 'department',
            22: 'referring_physician',          24: 'diagnosis_doctor',
            25: 'hospital',
        }
        while offset + 2 <= len(payload):
            tag = payload[offset]
            if tag == 0:
                break
            length = payload[offset + 1] if offset + 1 < len(payload) else 0
            offset += 2
            if offset + length > len(payload):
                break
            value = payload[offset: offset + length]
            offset += length
            key = TAG_MAP.get(tag)
            if not key:
                continue
            if tag in (2, 3, 4, 5, 16, 17, 19, 20, 22, 24, 25):
                demo[key] = value.rstrip(b'\x00').decode('latin-1', errors='ignore').strip()
            elif tag == 6:   # age
                if len(value) >= 3:
                    age = struct.unpack_from('<H', value)[0]
                    unit = {1:'years',2:'months',3:'weeks',4:'days'}.get(value[2],'years')
                    demo[key] = f"{age} {unit}" if age else None
            elif tag == 7:   # dob
                if len(value) >= 4:
                    yr,mo,dy = struct.unpack_from('<H',value)[0], value[2], value[3]
                    demo[key] = f"{yr:04d}-{mo:02d}-{dy:02d}" if yr and mo and dy else None
            elif tag == 8:   # height
                if len(value) >= 2:
                    v = struct.unpack_from('<H',value)[0]
                    demo[key] = f"{v} cm" if v else None
            elif tag == 9:   # weight
                if len(value) >= 2:
                    v = struct.unpack_from('<H',value)[0]
                    demo[key] = f"{v} kg" if v else None
            elif tag == 10:  # sex
                demo[key] = {0:'Unknown',1:'Male',2:'Female'}.get(value[0] if value else 0,'Unknown')
            elif tag in (14, 15):  # date/time
                if tag == 14 and len(value) >= 4:
                    yr,mo,dy = struct.unpack_from('<H',value)[0], value[2], value[3]
                    demo[key] = f"{yr:04d}-{mo:02d}-{dy:02d}" if yr and mo and dy else None
                elif tag == 15 and len(value) >= 3:
                    demo[key] = f"{value[0]:02d}:{value[1]:02d}:{value[2]:02d}"
        return demo

    # ── Section 7: Global measurements ────────────────────────────────────────
    def _decode_section7(self) -> dict:
        payload = self._get_payload(7)
        if len(payload) < 16:
            return {}
        try:
            meas = {
                'p_duration_ms':    struct.unpack_from('<H', payload, 0)[0],
                'pr_interval_ms':   struct.unpack_from('<H', payload, 2)[0],
                'qrs_duration_ms':  struct.unpack_from('<H', payload, 4)[0],
                'qt_interval_ms':   struct.unpack_from('<H', payload, 6)[0],
                'qtc_interval_ms':  struct.unpack_from('<H', payload, 8)[0],
                'p_axis_degrees':   struct.unpack_from('<h', payload, 10)[0],
                'qrs_axis_degrees': struct.unpack_from('<h', payload, 12)[0],
                't_axis_degrees':   struct.unpack_from('<h', payload, 14)[0],
            }
            if len(payload) >= 20:
                meas['ventricular_rate'] = struct.unpack_from('<H', payload, 16)[0]
                meas['atrial_rate']      = struct.unpack_from('<H', payload, 18)[0]
            # Remove invalid sentinel values
            INVALID = {0, 0x7FFF, 0x8000, 0xFFFF, 32767, -32768}
            return {k: v for k, v in meas.items() if v not in INVALID}
        except Exception:
            return {}

    # ── Section 3: Lead definition ─────────────────────────────────────────────
    def _decode_section3(self) -> dict:
        payload = self._get_payload(3)
        if len(payload) < 7:
            return {}
        try:
            num_leads   = payload[0]
            ref_samples = struct.unpack_from('<I', payload, 1)[0] if len(payload) > 4 else 0
            sample_rate = struct.unpack_from('<H', payload, 5)[0] if len(payload) > 6 else 500
            leads = []
            offset = 7
            for i in range(min(num_leads, 16)):
                if offset + 9 > len(payload):
                    break
                start   = struct.unpack_from('<I', payload, offset)[0]
                end     = struct.unpack_from('<I', payload, offset + 4)[0]
                lead_id = payload[offset + 8] if offset + 8 < len(payload) else i
                leads.append({
                    'id': lead_id,
                    'name': LEAD_NAMES[lead_id] if lead_id < len(LEAD_NAMES) else f'Lead{lead_id}',
                    'num_samples': max(0, end - start + 1),
                })
                offset += 9
            return {'num_leads': num_leads, 'sample_rate': sample_rate,
                    'ref_samples': ref_samples, 'leads': leads}
        except Exception:
            return {}

    # ── Section 6: Rhythm data header ─────────────────────────────────────────
    def _decode_section6(self) -> dict:
        payload = self._get_payload(6)
        if len(payload) < 4:
            return {}
        try:
            amp_res  = struct.unpack_from('<H', payload, 0)[0]  # nV/LSB
            samp_time= struct.unpack_from('<H', payload, 2)[0]  # µs/sample
            rate     = int(1_000_000 / samp_time) if samp_time > 0 else 500
            return {'amplitude_resolution_nv': amp_res,
                    'sample_time_us': samp_time,
                    'sample_rate_hz': rate}
        except Exception:
            return {}

    # ── Section 8/9: Clinical text ─────────────────────────────────────────────
    def _decode_text_section(self, sec_id: int) -> str:
        payload = self._get_payload(sec_id)
        if not payload:
            return ''
        try:
            return payload.rstrip(b'\x00').decode('latin-1', errors='ignore').strip()
        except Exception:
            return ''

    # ── Extractors ────────────────────────────────────────────────────────────
    def _extract_patient(self, fname_data: dict) -> dict:
        sec1 = self._decode_section1()

        # Merge: SCP section1 takes priority, filename fills gaps
        patient_id   = sec1.get('patient_id')   or fname_data.get('patient_id')
        patient_name = None
        first_name   = sec1.get('first_name')   or fname_data.get('patient_first_name')
        last_name    = sec1.get('last_name')     or fname_data.get('patient_last_name')

        if first_name or last_name:
            patient_name = ' '.join(filter(None, [first_name, last_name]))
        elif fname_data.get('patient_name'):
            patient_name = fname_data['patient_name']

        return {
            'id':                   patient_id,
            'name':                 patient_name,
            'first_name':           first_name,
            'last_name':            last_name,
            'dob':                  sec1.get('dob'),
            'age':                  sec1.get('age'),
            'sex':                  sec1.get('sex'),
            'weight':               sec1.get('weight'),
            'height':               sec1.get('height'),
            'room':                 sec1.get('room'),
            'hospital':             sec1.get('hospital'),
            'department':           sec1.get('department'),
            'referring_physician':  sec1.get('referring_physician'),
            'diagnosis_doctor':     sec1.get('diagnosis_doctor'),
            'technician':           sec1.get('technician'),
        }

    def _extract_recording(self, fname_data: dict) -> dict:
        sec1 = self._decode_section1()
        sec3 = self._decode_section3()
        sec6 = self._decode_section6()

        rec_date = sec1.get('rec_date') or fname_data.get('rec_date')
        rec_time = sec1.get('rec_time') or fname_data.get('rec_time')
        rec_dt   = f"{rec_date}T{rec_time}" if rec_date and rec_time else None

        sr       = sec6.get('sample_rate_hz') or sec3.get('sample_rate', 500)
        leads    = sec3.get('leads', [])
        max_samp = max((l['num_samples'] for l in leads), default=0)
        duration = round(max_samp / sr, 2) if sr and max_samp else None

        return {
            'date':           rec_date,
            'time':           rec_time,
            'datetime':       rec_dt,
            'device':         sec1.get('device', 'Edan SE-1200 Express'),
            'sample_rate_hz': sr,
            'num_leads':      sec3.get('num_leads', 12),
            'duration_sec':   duration,
            'amplitude_resolution_nv': sec6.get('amplitude_resolution_nv'),
        }

    def _extract_measurements(self) -> dict:
        s7   = self._decode_section7()
        hr   = s7.get('ventricular_rate')
        qtc  = s7.get('qtc_interval_ms')
        axis = s7.get('qrs_axis_degrees')

        # Interpretations
        hr_interp   = None
        if hr:
            if hr < 60:    hr_interp = 'Bradycardia'
            elif hr <= 100: hr_interp = 'Normal'
            else:           hr_interp = 'Tachycardia'

        qtc_interp  = None
        if qtc:
            if qtc < 350:    qtc_interp = 'Short QTc'
            elif qtc <= 440: qtc_interp = 'Normal QTc'
            elif qtc <= 470: qtc_interp = 'Borderline prolonged QTc'
            else:             qtc_interp = 'Prolonged QTc'

        axis_interp = None
        if axis is not None:
            if -30 <= axis <= 90:  axis_interp = 'Normal axis'
            elif axis < -30:       axis_interp = 'Left axis deviation'
            else:                  axis_interp = 'Right axis deviation'

        return {
            'heart_rate':  {'value': hr or None, 'unit': 'bpm', 'interp': hr_interp},
            'atrial_rate': {'value': s7.get('atrial_rate') or None, 'unit': 'bpm'},
            'intervals': {
                'p_duration_ms':     s7.get('p_duration_ms'),
                'pr_ms':             s7.get('pr_interval_ms'),
                'qrs_ms':            s7.get('qrs_duration_ms'),
                'qt_ms':             s7.get('qt_interval_ms'),
                'qtc_ms':            qtc,
                'qtc_interpretation':qtc_interp,
            },
            'axes': {
                'p_degrees':   s7.get('p_axis_degrees'),
                'qrs_degrees': axis,
                'qrs_interp':  axis_interp,
                't_degrees':   s7.get('t_axis_degrees'),
            },
        }

    def _extract_leads(self) -> list:
        sec3 = self._decode_section3()
        sec6 = self._decode_section6()
        sr   = sec6.get('sample_rate_hz', 500) or 500
        leads = sec3.get('leads', [])
        if not leads:
            leads = [{'id':i,'name':LEAD_NAMES[i],'num_samples':0} for i in range(12)]
        return [{
            'id':          l['id'],
            'name':        l['name'],
            'num_samples': l['num_samples'],
            'duration_ms': round(l['num_samples'] / (sr / 1000), 2) if l['num_samples'] else None,
        } for l in leads]

    def _extract_diagnosis(self) -> dict:
        clinical = self._decode_text_section(8)
        free_txt = self._decode_text_section(9)
        return {
            'clinical_summary': clinical or None,
            'free_text':        free_txt  or None,
            'auto_diagnosis':   self._auto_diagnose(),
        }

    def _auto_diagnose(self) -> list:
        s7  = self._decode_section7()
        hr  = s7.get('ventricular_rate', 0)
        pr  = s7.get('pr_interval_ms', 0)
        qrs = s7.get('qrs_duration_ms', 0)
        qtc = s7.get('qtc_interval_ms', 0)
        dx  = []
        if not any([hr, pr, qrs, qtc]):
            return ['Measurements not available — clinical review required']
        if 60 <= hr <= 100 and 120 <= pr <= 200 and qrs < 120:
            dx.append('Normal Sinus Rhythm')
        else:
            if hr and hr < 60:    dx.append('Sinus Bradycardia')
            if hr and hr > 100:   dx.append('Sinus Tachycardia')
            if pr and pr > 200:   dx.append('First Degree AV Block')
            if qrs and qrs > 120: dx.append('Bundle Branch Block')
            if qtc and qtc > 450: dx.append('Prolonged QT Interval')
        return dx or ['Clinical review required']

    def _build_interpretation(self, meas: dict) -> dict:
        findings = []
        flags    = []

        hr_obj = meas.get('heart_rate', {})
        hr     = hr_obj.get('value')
        if hr:
            findings.append(f"Heart rate: {hr} bpm ({hr_obj.get('interp','')})")
            if hr < 40 or hr > 180:
                flags.append(f"CRITICAL: Heart rate {hr} bpm — out of safe range")

        ivl = meas.get('intervals', {})
        pr  = ivl.get('pr_ms')
        if pr:
            findings.append(f"PR interval: {pr} ms")
            if pr > 200: flags.append("Prolonged PR interval — consider AV block")

        qrs = ivl.get('qrs_ms')
        if qrs:
            findings.append(f"QRS duration: {qrs} ms")
            if qrs > 120: flags.append("Wide QRS — consider bundle branch block")

        qtc = ivl.get('qtc_ms')
        if qtc:
            findings.append(f"QTc: {qtc} ms ({ivl.get('qtc_interpretation','')})")
            if qtc > 500: flags.append("CRITICAL: Very prolonged QTc — risk of arrhythmia")

        axes = meas.get('axes', {})
        ax   = axes.get('qrs_degrees')
        if ax is not None:
            findings.append(f"QRS axis: {ax}° ({axes.get('qrs_interp','')})")

        return {
            'findings': findings,
            'flags':    flags,
            'normal':   len(flags) == 0 and len(findings) > 0,
            'summary':  '; '.join(findings) if findings else 'Measurements not available in this file',
        }

    # ── Log output ────────────────────────────────────────────────────────────
    def to_log(self, result: dict) -> str:
        p   = result['patient']
        rec = result['recording']
        m   = result['measurements']
        d   = result['diagnosis']
        i   = result['interpretation']
        sep = '═' * 64

        lines = [
            sep,
            f"  ECG REPORT  —  {result['file']['name']}",
            f"  Parsed     : {result['file']['parsed_at']}",
            sep, '',
            '── RECORDING ' + '─'*51,
            f"  Date/Time  : {rec.get('datetime','N/A')}",
            f"  Device     : {rec.get('device','N/A')}",
            f"  Sample Rate: {rec.get('sample_rate_hz','N/A')} Hz",
            f"  Leads      : {rec.get('num_leads','N/A')}",
            f"  Duration   : {rec.get('duration_sec','N/A')} sec",
            '',
            '── PATIENT ' + '─'*53,
        ]
        for k, v in p.items():
            if v:
                lines.append(f"  {k.replace('_',' ').title():25s}: {v}")

        lines += ['', '── MEASUREMENTS ' + '─'*48]
        hr = m.get('heart_rate', {})
        if hr.get('value'):
            lines.append(f"  Heart Rate  : {hr['value']} bpm  [{hr.get('interp','')}]")
        ivl = m.get('intervals', {})
        for label, key in [('PR Interval','pr_ms'),('QRS Duration','qrs_ms'),
                            ('QT Interval','qt_ms'),('QTc Interval','qtc_ms')]:
            v = ivl.get(key)
            if v: lines.append(f"  {label:12s}: {v} ms")
        if ivl.get('qtc_interpretation'):
            lines.append(f"  QTc Interp  : {ivl['qtc_interpretation']}")
        axes = m.get('axes', {})
        for label, key in [('P Axis','p_degrees'),('QRS Axis','qrs_degrees'),('T Axis','t_degrees')]:
            v = axes.get(key)
            if v is not None: lines.append(f"  {label:12s}: {v}°")

        lines += ['', '── INTERPRETATION ' + '─'*46]
        for f in i.get('findings', []):
            lines.append(f"  • {f}")
        if i.get('flags'):
            lines += ['', '  ⚠ FLAGS:']
            for fl in i['flags']:
                lines.append(f"    ⚠  {fl}")

        lines += ['', '── AUTO DIAGNOSIS ' + '─'*46]
        for dx in d.get('auto_diagnosis', []):
            lines.append(f"  → {dx}")

        if d.get('clinical_summary'):
            lines += ['', '── CLINICAL SUMMARY ' + '─'*44, f"  {d['clinical_summary']}"]

        lines += ['', '── LEADS ' + '─'*55]
        for lead in result.get('leads', []):
            n = lead.get('num_samples', 0)
            dur = f"  ({lead['duration_ms']} ms)" if lead.get('duration_ms') else ''
            lines.append(f"  {lead['name']:6s}: {n:6d} samples{dur}")

        lines += ['', sep,
                  f"  File size  : {result['file']['size_bytes']:,} bytes",
                  sep]
        return '\n'.join(lines)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 scp_parser.py <file.scp> [--json|--log]")
        sys.exit(1)

    fp = sys.argv[1]
    if not os.path.exists(fp):
        print(f"File not found: {fp}", file=sys.stderr)
        sys.exit(1)

    parser = EdanSCPParser(fp)
    result = parser.parse()

    if '--log' in sys.argv:
        print(parser.to_log(result))
    else:
        print(json.dumps(result, indent=2, default=str))