"""Offline, fail-closed selection of pinned C9 diagnostic experiments."""
from pathlib import Path
import hashlib, json

VARIANTS = {
    'cong': 'build/c9_ddr_probe_20261101',
    'speed': 'build/c9_ddr_probe_speed_20261101',
    'nopack': 'build/c9_ddr_probe_nopack_20261101',
    'display': 'build/c9_display_fix_20261102',
    'geometry': 'build/c9_camera_geometry_image_20261102',
}

def select(root, variant):
    root = Path(root)
    project = root/VARIANTS[variant]
    path = project/'implementation_audit.json'
    audit = json.loads(path.read_text(encoding='utf-8-sig'))
    assert audit['status'] == 'PASS_OFFLINE_READONLY_DDR_PROBE', 'Probe implementation not qualified'
    assert audit['board_test_passed'] is False and audit['flash_written'] is False
    image = project/'outflow/soc_physical.bit'
    key = image.relative_to(root).as_posix()
    assert key in audit['evidence_sha256'], 'Image not bound by implementation audit'
    for field in ['source_sha256', 'evidence_sha256']:
        assert audit[field], 'Empty identity manifest'
        for name, digest in audit[field].items():
            p = (root/name).resolve()
            assert p.is_relative_to(root.resolve()), 'Identity path outside project'
            assert hashlib.sha256(p.read_bytes()).hexdigest() == digest, 'Changed audited input: '+name
    return image, path

def select_current(root,profile_name=None):
    """Resolve the board-qualified DDR diagnostic without selecting old COMB4=1."""
    root=Path(root)
    if profile_name is None:
        active=root/'config/c9_active_profile.json'
        profile_path=active if active.exists() else root/'config/c9_board_profile_20261102.json'
    else:profile_path=root/profile_name
    profile=json.loads(profile_path.read_text())
    assert profile['status']=='QUALIFIED_DDR_DIAGNOSTIC' and profile['variant'] in ['nopack','display']
    assert profile['pack_luts_to_comb4']==0 and profile['ddr_parameters_changed'] is False
    assert profile['calibration_algorithm_changed'] is False and profile['acceptance_criteria_changed'] is False
    image,audit=select(root,profile['variant'])
    assert hashlib.sha256(image.read_bytes()).hexdigest()==profile['image_sha256']
    assert hashlib.sha256(audit.read_bytes()).hexdigest()==profile['implementation_audit_sha256']
    from check_c9_ddr_calibration import check
    assert len(profile['calibration_attempts'])>=2
    for item in profile['calibration_attempts']:
        p=(root/item['path']).resolve();assert p.is_relative_to(root.resolve())
        assert hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256']
        assert check(p,audit)['calibration_verified'],'Profile calibration evidence failed'
    return image,audit,profile_path
