#!/usr/bin/env python3
"""
Kakao Bot Builder API에서 시나리오를 조회하고 필터링하는 스크립트
"""

import requests
import json
import sys
import os
import re
from typing import List, Dict, Optional, Tuple


def load_env_file(env_path: str = '.env') -> None:
    """
    .env 파일에서 환경변수를 로드합니다.
    
    Args:
        env_path: .env 파일 경로
    """
    if not os.path.exists(env_path):
        return
    
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 주석이나 빈 줄 건너뛰기
                if not line or line.startswith('#'):
                    continue
                # KEY=VALUE 형식 파싱
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    # 따옴표 제거 (시작과 끝이 같은 따옴표로 감싸져 있는 경우만)
                    if len(value) >= 2:
                        if (value.startswith('"') and value.endswith('"')) or \
                           (value.startswith("'") and value.endswith("'")):
                            value = value[1:-1]
                    # 환경변수가 이미 설정되어 있지 않으면 설정
                    if key and not os.getenv(key):
                        os.environ[key] = value
    except Exception as e:
        print(f"⚠️  .env 파일 로드 실패: {e}", file=sys.stderr)


def fetch_scenarios(api_url: str, cookie: Optional[str] = None) -> Dict:
    """
    API에서 시나리오 목록을 가져옵니다.
    
    Args:
        api_url: API 엔드포인트 URL
        cookie: 인증 쿠키 (선택사항)
    
    Returns:
        API 응답 데이터
    """
    headers = {
        'Content-Type': 'application/json',
        'authority': 'botbuilder-meta.kakao.com',
        'Access-Control-Allow-Origin': 'https://chatbot.kakao.com',
        'Referer': 'https://chatbot.kakao.com/',
    }
    
    if cookie:
        headers['Cookie'] = cookie
    
    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API 요청 실패: {e}", file=sys.stderr)
        if hasattr(e, 'response') and e.response is not None:
            print(f"응답 내용: {e.response.text}", file=sys.stderr)
        sys.exit(1)


def extract_items(data: Dict) -> List[Dict]:
    """
    응답 데이터에서 시나리오 리스트를 추출합니다.
    
    Args:
        data: API 응답 데이터
    
    Returns:
        시나리오 리스트
    """
    # 에러 응답 확인
    if data.get('status') == 'fail':
        error_data = data.get('data', {})
        error_code = error_data.get('code', 'N/A')
        error_message = error_data.get('message', '알 수 없는 오류')
        print(f"\n❌ API 요청 실패:", file=sys.stderr)
        print(f"   코드: {error_code}", file=sys.stderr)
        print(f"   메시지: {error_message}", file=sys.stderr)
        
        if error_code == 21001:  # 인증 실패
            print(f"\n💡 인증 쿠키가 필요합니다.", file=sys.stderr)
            print(f"   다음 중 하나의 방법으로 쿠키를 제공하세요:", file=sys.stderr)
            print(f"   1. 환경변수: export KAKAO_COOKIE='your_cookie_string'", file=sys.stderr)
            print(f"   2. 명령줄: python filter_scenarios.py --cookie='your_cookie_string'", file=sys.stderr)
        
        sys.exit(1)
    
    if 'data' not in data:
        print("응답에 'data' 필드가 없습니다.", file=sys.stderr)
        print(f"응답 내용: {json.dumps(data, indent=2, ensure_ascii=False)}")
        sys.exit(1)
    
    # data가 배열인 경우 (성공 응답)
    if isinstance(data['data'], list):
        return data['data']
    
    # data가 객체이고 items가 있는 경우 (다른 응답 형식)
    if isinstance(data['data'], dict) and 'items' in data['data']:
        return data['data']['items']
    
    print("응답 형식을 인식할 수 없습니다.", file=sys.stderr)
    print(f"응답 내용: {json.dumps(data, indent=2, ensure_ascii=False)}")
    sys.exit(1)


def display_all_scenarios(scenarios: List[Dict]):
    """
    모든 시나리오를 출력합니다.
    
    Args:
        scenarios: 시나리오 리스트
    """
    if not scenarios:
        print("시나리오가 없습니다.")
        return
    
    print(f"\n총 {len(scenarios)}개의 시나리오:\n")
    print("=" * 80)
    
    for scenario in scenarios:
        scenario_id = scenario.get('id', 'N/A')
        scenario_name = scenario.get('name', 'N/A')
        items = scenario.get('items', [])
        
        print(f"시나리오 ID: {scenario_id}")
        print(f"시나리오 Name: {scenario_name}")
        print(f"블록 개수: {len(items)}")
        print("-" * 80)
        
        if items:
            # 블록 ID와 Name을 쌍으로 묶어서 출력
            for idx, item in enumerate(items, 1):
                block_id = item.get('id', 'N/A')
                block_name = item.get('name', 'N/A')
                print(f"  [{idx}] 블록 ID: {block_id} | 블록 Name: {block_name}")
        else:
            print("  (블록이 없습니다)")
        
        print("=" * 80)
        print()


def search_blocks(scenarios: List[Dict], search_term: str) -> List[Dict]:
    """
    시나리오의 블록들에서 검색어로 필터링합니다.
    
    Args:
        scenarios: 시나리오 리스트
        search_term: 검색어
    
    Returns:
        필터링된 블록 리스트 (시나리오 정보 포함)
    """
    if not search_term:
        return []
    
    search_term_lower = search_term.lower()
    results = []
    
    for scenario in scenarios:
        scenario_id = scenario.get('id', 'N/A')
        scenario_name = scenario.get('name', 'N/A')
        items = scenario.get('items', [])
        
        for item in items:
            block_id = item.get('id', 'N/A')
            block_name = item.get('name', '')
            
            # 블록 이름에서 검색
            if search_term_lower in block_name.lower():
                results.append({
                    'scenario_id': scenario_id,
                    'scenario_name': scenario_name,
                    'block_id': block_id,
                    'block_name': block_name
                })
    
    return results


def display_search_results(results: List[Dict]):
    """
    검색 결과를 출력합니다.
    
    Args:
        results: 검색 결과 리스트
    """
    if not results:
        print("검색 결과가 없습니다.")
        return
    
    print(f"\n총 {len(results)}개의 블록을 찾았습니다:\n")
    print("-" * 80)
    
    for idx, result in enumerate(results, 1):
        print(f"[{idx}] 시나리오 ID: {result['scenario_id']} | 시나리오 Name: {result['scenario_name']}")
        print(f"    블록 ID: {result['block_id']} | 블록 Name: {result['block_name']}")
        print("-" * 80)


def search_blocks_by_id(scenarios: List[Dict], block_id: str) -> Optional[Dict]:
    """
    블록 ID로 블록을 검색합니다.
    
    Args:
        scenarios: 시나리오 리스트
        block_id: 검색할 블록 ID
    
    Returns:
        찾은 블록 정보 또는 None
    """
    for scenario in scenarios:
        scenario_id = scenario.get('id', 'N/A')
        scenario_name = scenario.get('name', 'N/A')
        items = scenario.get('items', [])
        
        for item in items:
            if item.get('id') == block_id:
                return {
                    'scenario_id': scenario_id,
                    'scenario_name': scenario_name,
                    'block_id': block_id,
                    'block_name': item.get('name', 'N/A')
                }
    
    return None


def find_matching_blocks_in_other_envs(env_scenarios: Dict[str, List[Dict]], 
                                        source_env: str, 
                                        scenario_name: str, 
                                        block_name: str) -> Dict[str, Optional[Dict]]:
    """
    다른 환경에서 동일한 시나리오의 블록을 찾습니다.
    
    Args:
        env_scenarios: 환경별 시나리오 딕셔너리
        source_env: 원본 환경 이름
        scenario_name: 시나리오 이름
        block_name: 블록 이름
    
    Returns:
        환경별 블록 정보 딕셔너리 {env_name: block_info or None}
    """
    results = {}
    
    for env_name, scenarios in env_scenarios.items():
        if not scenarios:
            results[env_name] = None
            continue
        
        # 같은 시나리오 이름 찾기
        matching_scenario = None
        for scenario in scenarios:
            if scenario.get('name') == scenario_name:
                matching_scenario = scenario
                break
        
        if not matching_scenario:
            results[env_name] = None
            continue
        
        # 같은 블록 이름 찾기
        items = matching_scenario.get('items', [])
        matching_block = None
        for item in items:
            if item.get('name') == block_name:
                matching_block = {
                    'scenario_id': matching_scenario.get('id', 'N/A'),
                    'scenario_name': scenario_name,
                    'block_id': item.get('id', 'N/A'),
                    'block_name': block_name
                }
                break
        
        results[env_name] = matching_block
    
    return results


def search_blocks_multi_env(env_scenarios: Dict[str, List[Dict]], search_term: str) -> Dict[str, List[Dict]]:
    """
    여러 환경에서 블록을 검색합니다.
    
    Args:
        env_scenarios: 환경별 시나리오 딕셔너리 {env_name: scenarios}
        search_term: 검색어 (블록 이름 또는 블록 ID)
    
    Returns:
        환경별 검색 결과 딕셔너리 {env_name: results}
    """
    results = {}
    
    for env_name, scenarios in env_scenarios.items():
        if scenarios:
            results[env_name] = search_blocks(scenarios, search_term)
        else:
            results[env_name] = []
    
    return results


def search_by_block_id_multi_env(env_scenarios: Dict[str, List[Dict]], block_id: str) -> Dict[str, Optional[Dict]]:
    """
    여러 환경에서 블록 ID로 검색하고, 다른 환경의 동일 블록을 찾습니다.
    
    Args:
        env_scenarios: 환경별 시나리오 딕셔너리
        block_id: 검색할 블록 ID
    
    Returns:
        환경별 블록 정보 딕셔너리 {env_name: block_info or None}
    """
    # 모든 환경에서 해당 block id 찾기
    found_blocks = {}
    source_info = None
    
    for env_name, scenarios in env_scenarios.items():
        if scenarios:
            block_info = search_blocks_by_id(scenarios, block_id)
            found_blocks[env_name] = block_info
            if block_info and source_info is None:
                source_info = block_info
                source_info['env'] = env_name
        else:
            found_blocks[env_name] = None
    
    # source_info가 있으면, 다른 환경에서 같은 시나리오의 같은 블록 찾기
    if source_info:
        scenario_name = source_info['scenario_name']
        block_name = source_info['block_name']
        
        # 다른 환경에서 매칭되는 블록 찾기
        matching_blocks = find_matching_blocks_in_other_envs(
            env_scenarios, 
            source_info['env'], 
            scenario_name, 
            block_name
        )
        
        # 찾은 블록과 매칭된 블록 병합
        for env_name in matching_blocks:
            if matching_blocks[env_name] and not found_blocks[env_name]:
                found_blocks[env_name] = matching_blocks[env_name]
    
    return found_blocks


def display_block_id_search_results(env_results: Dict[str, Optional[Dict]], search_block_id: str):
    """
    블록 ID 검색 결과를 출력합니다.
    
    Args:
        env_results: 환경별 블록 정보 딕셔너리
        search_block_id: 검색한 블록 ID
    """
    found_count = sum(1 for result in env_results.values() if result is not None)
    
    if found_count == 0:
        print(f"블록 ID '{search_block_id}'를 찾을 수 없습니다.")
        return
    
    # 첫 번째로 찾은 블록 정보
    first_result = next((result for result in env_results.values() if result), None)
    if first_result:
        print(f"\n블록 ID '{search_block_id}' 검색 결과:")
        print(f"시나리오: {first_result['scenario_name']}")
        print(f"블록 Name: {first_result['block_name']}")
        print("=" * 80)
    
    for env_name in ['dev', 'prod', 'stg']:
        if env_name in env_results:
            result = env_results[env_name]
            if result:
                print(f"[{env_name.upper()}] 시나리오 ID: {result['scenario_id']} | 블록 ID: {result['block_id']}")
            else:
                print(f"[{env_name.upper()}] 없음")
    
    print("=" * 80)


def parse_block_ids_from_text(text: str) -> List[Tuple[str, str, int]]:
    """
    YAML 형식의 텍스트에서 블록 ID를 파싱합니다.
    
    Args:
        text: YAML 형식의 텍스트
    
    Returns:
        (block_id, path, line_number) 튜플 리스트
    """
    block_ids = []
    lines = text.split('\n')
    path_stack = []  # 계층 구조 추적
    # 블록 ID 패턴: 변수명: block_id # 주석 형식
    # block_id는 24자리 16진수 문자열
    block_id_pattern = re.compile(r'^(\s*)([a-zA-Z_][a-zA-Z0-9_]*):\s*([a-f0-9]{24})\s*(?:#.*)?$', re.IGNORECASE)
    
    for line_num, line in enumerate(lines, 1):
        original_line = line
        line = line.rstrip()
        
        # 빈 줄 건너뛰기
        if not line.strip():
            continue
        
        # 주석만 있는 줄 건너뛰기
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        
        # 블록 ID 패턴 매칭 (변수명: block_id # 주석 형식)
        match = block_id_pattern.match(line)
        if match:
            indent = len(match.group(1))
            var_name = match.group(2)
            block_id = match.group(3)
            
            # 현재 들여쓰기 레벨에 맞게 path_stack 조정
            while path_stack and path_stack[-1][1] >= indent:
                path_stack.pop()
            
            # 경로 구성
            if path_stack:
                path = '.'.join([p[0] for p in path_stack] + [var_name])
            else:
                path = var_name
            
            path_stack.append((var_name, indent))
            block_ids.append((block_id, path, line_num))
        else:
            # 블록 ID가 아닌 키-값 쌍인 경우 (예: hsptlzInfo: # 입원 확인)
            # 경로 스택에 추가만 하고 블록 ID는 추가하지 않음
            key_value_pattern = re.compile(r'^(\s*)([a-zA-Z_][a-zA-Z0-9_]*):\s*(?:#.*)?$')
            key_match = key_value_pattern.match(line)
            if key_match:
                indent = len(key_match.group(1))
                var_name = key_match.group(2)
                
                # 현재 들여쓰기 레벨에 맞게 path_stack 조정
                while path_stack and path_stack[-1][1] >= indent:
                    path_stack.pop()
                
                path_stack.append((var_name, indent))
    
    return block_ids


def validate_block_ids(block_ids: List[Tuple[str, str, int]], 
                       scenarios: List[Dict], 
                       env_name: str) -> List[Dict]:
    """
    블록 ID 목록이 해당 환경에서 유효한지 검증합니다.
    
    Args:
        block_ids: (block_id, path, line_number) 튜플 리스트
        scenarios: 시나리오 리스트
        scenarios: 환경 이름
    
    Returns:
        검증 결과 리스트
    """
    # 모든 블록 ID를 딕셔너리로 변환 (빠른 검색을 위해)
    all_blocks = {}
    for scenario in scenarios:
        scenario_id = scenario.get('id', 'N/A')
        scenario_name = scenario.get('name', 'N/A')
        items = scenario.get('items', [])
        
        for item in items:
            block_id = item.get('id', 'N/A')
            block_name = item.get('name', 'N/A')
            all_blocks[block_id] = {
                'scenario_id': scenario_id,
                'scenario_name': scenario_name,
                'block_name': block_name
            }
    
    # 검증 결과
    results = []
    for block_id, path, line_num in block_ids:
        if block_id in all_blocks:
            block_info = all_blocks[block_id]
            results.append({
                'block_id': block_id,
                'path': path,
                'line_number': line_num,
                'valid': True,
                'scenario_id': block_info['scenario_id'],
                'scenario_name': block_info['scenario_name'],
                'block_name': block_info['block_name']
            })
        else:
            results.append({
                'block_id': block_id,
                'path': path,
                'line_number': line_num,
                'valid': False,
                'scenario_id': None,
                'scenario_name': None,
                'block_name': None
            })
    
    return results


def display_validation_results(results: List[Dict], env_name: str):
    """
    검증 결과를 출력합니다.
    
    Args:
        results: 검증 결과 리스트
        env_name: 환경 이름
    """
    valid_count = sum(1 for r in results if r['valid'])
    invalid_count = len(results) - valid_count
    
    print(f"\n[{env_name.upper()}] 블록 ID 검증 결과")
    print("=" * 80)
    print(f"총 {len(results)}개 중 유효: {valid_count}개, 무효: {invalid_count}개\n")
    
    # 유효한 블록들
    if valid_count > 0:
        print("✓ 유효한 블록 ID:")
        print("-" * 80)
        for result in results:
            if result['valid']:
                print(f"  [{result['line_number']:3d}] {result['path']}")
                print(f"       블록 ID: {result['block_id']}")
                print(f"       시나리오: {result['scenario_name']} | 블록: {result['block_name']}")
                print()
    
    # 무효한 블록들
    if invalid_count > 0:
        print("✗ 무효한 블록 ID:")
        print("-" * 80)
        for result in results:
            if not result['valid']:
                print(f"  [{result['line_number']:3d}] {result['path']}")
                print(f"       블록 ID: {result['block_id']} - 해당 환경에서 찾을 수 없음")
                print()
    
    print("=" * 80)


def display_search_results_multi_env(env_results: Dict[str, List[Dict]]):
    """
    여러 환경의 검색 결과를 비교하여 출력합니다.
    
    Args:
        env_results: 환경별 검색 결과 딕셔너리 {env_name: results}
    """
    # 전체 검색 결과 수집
    total_count = sum(len(results) for results in env_results.values())
    
    if total_count == 0:
        print("검색 결과가 없습니다.")
        return
    
    print(f"\n총 {total_count}개의 블록을 찾았습니다:\n")
    
    # 블록 이름 기준으로 그룹화
    block_groups = {}
    
    for env_name, results in env_results.items():
        for result in results:
            block_name = result['block_name']
            scenario_name = result['scenario_name']
            key = f"{scenario_name}::{block_name}"
            
            if key not in block_groups:
                block_groups[key] = {
                    'scenario_name': scenario_name,
                    'block_name': block_name,
                    'envs': {}
                }
            
            block_groups[key]['envs'][env_name] = {
                'scenario_id': result['scenario_id'],
                'block_id': result['block_id']
            }
    
    # 결과 출력
    print("=" * 80)
    for idx, (key, group) in enumerate(sorted(block_groups.items()), 1):
        print(f"[{idx}] 시나리오: {group['scenario_name']}")
        print(f"    블록 Name: {group['block_name']}")
        print("-" * 80)
        
        for env_name in ['dev', 'prod', 'stg']:
            if env_name in group['envs']:
                env_data = group['envs'][env_name]
                print(f"    [{env_name.upper()}] 시나리오 ID: {env_data['scenario_id']} | 블록 ID: {env_data['block_id']}")
            else:
                print(f"    [{env_name.upper()}] 없음")
        
        print("=" * 80)
        print()


def load_environment_data(env_name: str, api_url: str, cookie: Optional[str]) -> Optional[List[Dict]]:
    """
    특정 환경의 시나리오 데이터를 로드합니다.
    
    Args:
        env_name: 환경 이름 (dev, prod, stg)
        api_url: API URL
        cookie: 인증 쿠키
    
    Returns:
        시나리오 리스트 또는 None (실패 시)
    """
    print(f"\n[{env_name.upper()}] API 요청 중: {api_url}")
    if not cookie:
        print(f"⚠️  [{env_name.upper()}] 인증 쿠키가 제공되지 않았습니다.")
        return None
    
    try:
        response_data = fetch_scenarios(api_url, cookie)
        scenarios = extract_items(response_data)
        print(f"✓ [{env_name.upper()}] 총 {len(scenarios)}개의 시나리오를 가져왔습니다.")
        return scenarios
    except Exception as e:
        print(f"❌ [{env_name.upper()}] 데이터 로드 실패: {e}", file=sys.stderr)
        return None


def compare_environments(env_data: Dict[str, List[Dict]]):
    """
    여러 환경의 시나리오를 비교합니다.
    
    Args:
        env_data: 환경별 시나리오 데이터 딕셔너리 {env_name: scenarios}
    """
    print("\n" + "=" * 80)
    print("환경별 시나리오 비교")
    print("=" * 80)
    
    # 각 환경의 시나리오 이름 수집
    env_scenarios = {}
    for env_name, scenarios in env_data.items():
        if scenarios:
            env_scenarios[env_name] = {s.get('name', 'N/A'): s for s in scenarios}
        else:
            env_scenarios[env_name] = {}
    
    # 모든 시나리오 이름 수집
    all_scenario_names = set()
    for scenarios_dict in env_scenarios.values():
        all_scenario_names.update(scenarios_dict.keys())
    
    all_scenario_names = sorted(all_scenario_names)
    
    print(f"\n총 {len(all_scenario_names)}개의 고유 시나리오 발견\n")
    
    for scenario_name in all_scenario_names:
        print(f"시나리오: {scenario_name}")
        print("-" * 80)
        
        for env_name in ['dev', 'prod', 'stg']:
            if env_name in env_scenarios and scenario_name in env_scenarios[env_name]:
                scenario = env_scenarios[env_name][scenario_name]
                scenario_id = scenario.get('id', 'N/A')
                items_count = len(scenario.get('items', []))
                print(f"  [{env_name.upper()}] ID: {scenario_id} | 블록 개수: {items_count}")
            else:
                print(f"  [{env_name.upper()}] 없음")
        
        print()
    
    print("=" * 80)


def main():
    # .env 파일에서 환경변수 로드
    load_env_file()
    
    # 환경별 API URL 정의 (환경변수에서 가져오기)
    environments = {
        'dev': {
            'url': os.getenv('KAKAO_API_URL_DEV', 'https://botbuilder-meta.kakao.com/api/v2/bots/64bf85d984644d346efe4068/scenarios'),
            'cookie_key': 'KAKAO_COOKIE_DEV'
        },
        'prod': {
            'url': os.getenv('KAKAO_API_URL_PROD', 'https://botbuilder-meta.kakao.com/api/v2/bots/6360854319072f1bc647c920/scenarios'),
            'cookie_key': 'KAKAO_COOKIE_PROD'
        },
        'stg': {
            'url': os.getenv('KAKAO_API_URL_STG', 'https://botbuilder-meta.kakao.com/api/v2/bots/67d26be819ec670b29b1bb42/scenarios'),
            'cookie_key': 'KAKAO_COOKIE_STG'
        }
    }
    
    # 환경별 데이터 저장소
    env_scenarios = {}
    
    # 초기 로드: dev 환경만 먼저 로드
    dev_env = environments['dev']
    dev_cookie = os.getenv(dev_env['cookie_key']) or os.getenv('KAKAO_COOKIE')  # 하위 호환성
    dev_scenarios = load_environment_data('dev', dev_env['url'], dev_cookie)
    if dev_scenarios:
        env_scenarios['dev'] = dev_scenarios
    
    print()
    
    # 메인 루프
    def print_menu():
        print("=" * 80)
        print("명령어:")
        print("  0 또는 exit - 프로그램 종료")
        print("  1 - DEV 환경 전체 시나리오 출력")
        print("  2 - PROD 환경 전체 시나리오 출력")
        print("  3 - STG 환경 전체 시나리오 출력")
        print("  4 - 환경별 시나리오 비교")
        print("  5 - 블록 검색 모드 (DEV, PROD, STG 모든 환경)")
        print("  6 - 블록 ID 검증 (YAML 형식 텍스트)")
        print("=" * 80)
    
    print_menu()
    
    while True:
        try:
            user_input = input("\n> ").strip()
            
            # 2. 입력값이 "0" 또는 "exit"이면 프로그램 종료
            if user_input == "0" or user_input.lower() == "exit":
                print("프로그램을 종료합니다.")
                break
            
            # 3. 환경별 전체 시나리오 출력
            elif user_input == "1":  # DEV
                if 'dev' not in env_scenarios:
                    print("⚠️  DEV 환경 데이터가 없습니다. 먼저 로드해주세요.")
                else:
                    display_all_scenarios(env_scenarios['dev'])
                print_menu()
            
            elif user_input == "2":  # PROD
                if 'prod' not in env_scenarios:
                    # PROD 환경 데이터 로드
                    prod_env = environments['prod']
                    prod_cookie = os.getenv(prod_env['cookie_key'])
                    prod_scenarios = load_environment_data('prod', prod_env['url'], prod_cookie)
                    if prod_scenarios:
                        env_scenarios['prod'] = prod_scenarios
                
                if 'prod' in env_scenarios:
                    display_all_scenarios(env_scenarios['prod'])
                else:
                    print("⚠️  PROD 환경 데이터를 로드할 수 없습니다.")
                print_menu()
            
            elif user_input == "3":  # STG
                if 'stg' not in env_scenarios:
                    # STG 환경 데이터 로드
                    stg_env = environments['stg']
                    stg_cookie = os.getenv(stg_env['cookie_key'])
                    stg_scenarios = load_environment_data('stg', stg_env['url'], stg_cookie)
                    if stg_scenarios:
                        env_scenarios['stg'] = stg_scenarios
                
                if 'stg' in env_scenarios:
                    display_all_scenarios(env_scenarios['stg'])
                else:
                    print("⚠️  STG 환경 데이터를 로드할 수 없습니다.")
                print_menu()
            
            # 4. 환경별 비교
            elif user_input == "4":
                # 필요한 환경 데이터가 없으면 로드
                for env_name, env_config in environments.items():
                    if env_name not in env_scenarios:
                        cookie = os.getenv(env_config['cookie_key'])
                        if env_name == 'dev' and not cookie:
                            cookie = os.getenv('KAKAO_COOKIE')  # 하위 호환성
                        scenarios = load_environment_data(env_name, env_config['url'], cookie)
                        if scenarios:
                            env_scenarios[env_name] = scenarios
                
                if env_scenarios:
                    compare_environments(env_scenarios)
                else:
                    print("⚠️  비교할 환경 데이터가 없습니다.")
                print_menu()
            
            # 5. 블록 검색 모드 (모든 환경)
            elif user_input == "5":
                # 필요한 환경 데이터가 없으면 로드
                for env_name, env_config in environments.items():
                    if env_name not in env_scenarios:
                        cookie = os.getenv(env_config['cookie_key'])
                        if env_name == 'dev' and not cookie:
                            cookie = os.getenv('KAKAO_COOKIE')  # 하위 호환성
                        scenarios = load_environment_data(env_name, env_config['url'], cookie)
                        if scenarios:
                            env_scenarios[env_name] = scenarios
                
                if not env_scenarios:
                    print("⚠️  검색할 환경 데이터가 없습니다.")
                    print_menu()
                    continue
                
                print("\n[검색 모드] 블록 이름 또는 블록 ID로 검색합니다. (DEV, PROD, STG 모든 환경)")
                
                def print_search_menu():
                    print("-" * 80)
                    print("검색 모드 안내:")
                    print("  - 블록 이름으로 검색: 블록 이름의 일부를 입력")
                    print("  - 블록 ID로 검색: 정확한 블록 ID를 입력 (다른 환경의 동일 블록도 자동 검색)")
                    print("  - 0 또는 exit - 검색 모드 종료")
                    print("-" * 80)
                
                print_search_menu()
                
                # 검색 모드 루프
                while True:
                    try:
                        search_input = input("\n검색어> ").strip()
                        
                        # 검색 모드 종료
                        if search_input == "0" or search_input.lower() == "exit":
                            print("검색 모드를 종료합니다.")
                            print_menu()
                            break
                        
                        # 검색어로 검색
                        if search_input:
                            # 먼저 block ID로 검색 시도 (모든 환경에서)
                            block_id_found = False
                            for env_name, scenarios in env_scenarios.items():
                                if scenarios:
                                    block_info = search_blocks_by_id(scenarios, search_input)
                                    if block_info:
                                        block_id_found = True
                                        break
                            
                            if block_id_found:
                                # Block ID 검색 모드
                                env_results = search_by_block_id_multi_env(env_scenarios, search_input)
                                display_block_id_search_results(env_results, search_input)
                            else:
                                # 블록 이름 검색 모드
                                env_results = search_blocks_multi_env(env_scenarios, search_input)
                                display_search_results_multi_env(env_results)
                            
                            print_search_menu()
                        else:
                            print("검색어를 입력하세요.")
                            print_search_menu()
                    
                    except KeyboardInterrupt:
                        print("\n검색 모드를 종료합니다.")
                        print_menu()
                        break
            
            # 6. 블록 ID 검증
            elif user_input == "6":
                print("\n[블록 ID 검증 모드]")
                print("YAML 형식의 텍스트를 입력하세요. (입력 완료 후 빈 줄에서 Enter를 두 번 누르세요)")
                print("예시:")
                print("  hsptlzInfo: # 입원 확인")
                print("    hsplzInfoInquiry: 67d2804ef38a8bfdf0172bce # 입원정보조회")
                print("-" * 80)
                
                # 여러 줄 입력 받기
                lines = []
                empty_line_count = 0
                print("\n텍스트 입력 (빈 줄 두 번으로 종료):")
                try:
                    while True:
                        line = input()
                        if not line.strip():
                            empty_line_count += 1
                            if empty_line_count >= 2:
                                break
                        else:
                            empty_line_count = 0
                            lines.append(line)
                except KeyboardInterrupt:
                    print("\n입력이 취소되었습니다.")
                    print_menu()
                    continue
                
                if not lines:
                    print("입력된 텍스트가 없습니다.")
                    print_menu()
                    continue
                
                # 텍스트 파싱
                text = '\n'.join(lines)
                try:
                    block_ids = parse_block_ids_from_text(text)
                    
                    if not block_ids:
                        print("⚠️  블록 ID를 찾을 수 없습니다. 형식을 확인해주세요.")
                        print_menu()
                        continue
                    
                    print(f"\n✓ {len(block_ids)}개의 블록 ID를 찾았습니다.")
                    
                    # 환경 선택
                    print("\n검증할 환경을 선택하세요:")
                    print("  1 - DEV")
                    print("  2 - PROD")
                    print("  3 - STG")
                    
                    env_name = None
                    try:
                        while True:
                            env_choice = input("\n환경 선택 (1/2/3)> ").strip()
                            
                            if env_choice == "1":
                                env_name = 'dev'
                                break
                            elif env_choice == "2":
                                env_name = 'prod'
                                break
                            elif env_choice == "3":
                                env_name = 'stg'
                                break
                            else:
                                print("1, 2, 3 중 하나를 입력하세요.")
                    except KeyboardInterrupt:
                        print("\n취소되었습니다.")
                        print_menu()
                        continue
                    
                    if env_name:
                        # 선택한 환경 데이터 로드
                        if env_name not in env_scenarios:
                            env_config = environments[env_name]
                            cookie = os.getenv(env_config['cookie_key'])
                            if env_name == 'dev' and not cookie:
                                cookie = os.getenv('KAKAO_COOKIE')  # 하위 호환성
                            scenarios = load_environment_data(env_name, env_config['url'], cookie)
                            if scenarios:
                                env_scenarios[env_name] = scenarios
                        
                        if env_name in env_scenarios:
                            # 검증 수행
                            results = validate_block_ids(block_ids, env_scenarios[env_name], env_name)
                            display_validation_results(results, env_name)
                        else:
                            print(f"⚠️  {env_name.upper()} 환경 데이터를 로드할 수 없습니다.")
                    
                    print_menu()
                
                except Exception as e:
                    print(f"❌ 오류 발생: {e}", file=sys.stderr)
                    import traceback
                    traceback.print_exc()
                    print_menu()
            
            else:
                print("잘못된 명령어입니다. 0, 1, 2, 3, 4, 5, 6 중 하나를 입력하세요.")
                print_menu()
        
        except KeyboardInterrupt:
            print("\n프로그램을 종료합니다.")
            break


if __name__ == "__main__":
    main()

