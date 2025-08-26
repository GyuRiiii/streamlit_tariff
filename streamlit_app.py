import pandas as pd
import re
import numpy as np
import streamlit as st
import plotly.graph_objs as go
import plotly.express as px
from plotly.subplots import make_subplots
import seaborn as sns
from pathlib import Path

# =========================================
# 기본 설정
# =========================================
st.set_page_config(page_title="반도체 분야 관세율·협정 대시보드 (품목분류 기반)", layout="wide")

# ---------- 경로: 레포 내 data/ 폴더 기준 ----------
APP_DIR = Path(__file__).parent
DATA_DIR = APP_DIR / "data"
TARIFF_DIR = DATA_DIR / "tariff_semi"   # 예: data/tariff_semi/tariff_semi_2020_with_info.csv
HS_PATH = DATA_DIR / "unique_hscode_semi.csv"

YEARS = [2020, 2021, 2022, 2023, 2024, 2025]

# =========================================
# 유틸 함수
# =========================================
def _read_csv_safe(path: Path, **kwargs) -> pd.DataFrame:
    """utf-8-sig → utf-8 순서로 시도하여 안전하게 읽기"""
    try:
        return pd.read_csv(path, encoding="utf-8-sig", **kwargs)
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="utf-8", **kwargs)

@st.cache_data(show_spinner=False)
def load_data_all() -> pd.DataFrame:
    """data/tariff_semi 아래 연도별 파일을 모두 로드해 합치고 숫자 컬럼 생성"""
    dfs = []
    for y in YEARS:
        f = TARIFF_DIR / f"tariff_semi_{y}_with_info.csv"
        if not f.exists():
            continue
        df = _read_csv_safe(f, dtype=str)
        df["연도"] = y
        # 관세율 숫자형 변환
        if "관세율" in df.columns:
            df["관세율_num"] = pd.to_numeric(
                df["관세율"].str.replace(",", ""), errors="coerce"
            )
        dfs.append(df)
    if dfs:
        out = pd.concat(dfs, ignore_index=True)
        # 품목번호 표준화(공백 제거)
        if "품목번호" in out.columns:
            out["품목번호"] = out["품목번호"].astype(str).str.strip()
        return out
    return pd.DataFrame()

@st.cache_data(show_spinner=False)
def load_hs_list() -> list[str]:
    """data/unique_hscode_semi.csv에서 HS 목록 로드"""
    df_hs = _read_csv_safe(HS_PATH)
    col = "HS코드" if "HS코드" in df_hs.columns else df_hs.columns[0]
    hs_list = (
        df_hs[col]
        .astype(str)
        .dropna()
        .str.strip()
        .replace("", pd.NA)
        .dropna()
        .unique()
        .tolist()
    )
    return sorted(set(hs_list))

def token_match_country(series: pd.Series, country: str) -> pd.Series:
    """
    '브라질 미국 중국'처럼 공백 구분된 국가 문자열에서 토큰 매칭
    """
    patt = re.compile(rf"(?:^|\s){re.escape(country)}(?:\s|$)")
    out = series.astype(str).str.replace(r"\s+", " ", regex=True).str.strip().apply(
        lambda s: bool(patt.search(s))
    )
    out.index = series.index
    return out

def main():
    # =========================================
    # 데이터 로드
    # =========================================
    df = load_data_all()
    hs_list = load_hs_list()

    st.title("반도체 분야 관세율·협정 대시보드")
    st.sidebar.title("필터")

    # HS 코드 검색 + 후보
    q = st.sidebar.text_input("HS 코드 검색", value="", placeholder="예: 8486, 8542, ...")
    if q:
        candidates = [h for h in hs_list if h.startswith(q)]
        if not candidates:
            st.sidebar.warning("해당 패턴으로 시작하는 HS 코드가 없습니다.")
            candidates = hs_list
    else:
        candidates = hs_list

    hs_selected = st.sidebar.selectbox("HS코드 선택", candidates if candidates else [""])

    menu = st.sidebar.radio(
        "페이지",
        ["수입 관세율 조회", "연도별 관세 추이", "관세 이슈 키워드(예정)", "주요 국가별 해외 관세(예정)", "무역 동향(예정)"],
    )

    # 공통 가드
    if df.empty:
        st.error("데이터가 없습니다. 레포의 data/ 폴더와 파일명을 확인하세요.")
        return
    if "품목번호" not in df.columns:
        st.error("데이터에 '품목번호' 컬럼이 없습니다.")
        return

    df_sel = df[df["품목번호"] == hs_selected] if hs_selected else pd.DataFrame()
    if df_sel.empty:
        st.info("선택한 HS 코드에 해당하는 데이터가 없습니다.")
    else:
        # 대표 품목명 추출
        item_name = None
        for col in ["품명", "품목명", "이름", "소분류", "대분류"]:
            if col in df_sel.columns:
                vals = df_sel[col].dropna().unique()
                if len(vals) > 0:
                    item_name = vals[0]
                    break
        if item_name:
            st.markdown(f"**품목명:** {item_name}")

    # =========================================
    # 수입 관세율 조회
    # =========================================
    if menu == "수입 관세율 조회":
        COUNTRIES = [
            "그리스","네덜란드","노르웨이","뉴질랜드","니카라과","덴마크","독일","라오스","라트비아",
            "루마니아","룩셈부르크","리투아니아","리히텐슈타인","말레이시아","몰타","미국","미얀마",
            "방글라데시","베트남","벨기에","불가리아","브루나이","사이프러스","스리랑카","스웨덴",
            "스위스","스페인","슬로바키아","슬로베니아","싱가포르","아이슬란드","아일랜드","에스토니아",
            "엘살바도르","영국","오스트리아","온두라스","이스라엘","이탈리아","인도","인도네시아",
            "일본","중국","체코","칠레","캄보디아","캐나다","코스타리카","콜롬비아","크로아티아",
            "쿠웨이트","태국","터키","페루","포르투갈","폴란드","프랑스","핀란드","헝가리",
            "호주","홍콩"
        ]

        st.markdown("## 📌수입 관세율 조회")
        col1, col2 = st.columns(2)

        with col1:
            if df_sel.empty:
                st.info("선택한 HS 코드에 해당하는 데이터가 없습니다.")
            else:
                df_sel_2025 = df_sel[df_sel["연도"] == 2025] if "연도" in df_sel.columns else pd.DataFrame()
                st.markdown("### 2025년 관세 협정 / 관세율")
                if df_sel_2025.empty:
                    st.info("2025년 데이터가 없어요. 상단의 '연도별 관세 추이'에서 다른 연도를 확인해 보세요.")
                else:
                    show_cols = ["관세율구분값", "관세율"]
                    available = [c for c in show_cols if c in df_sel_2025.columns]
                    if not available:
                        st.info("표시 가능한 컬럼이 없습니다.")
                    else:
                        st.dataframe(
                            df_sel_2025[available].sort_values(available[-1]),
                            use_container_width=True,
                            hide_index=True
                        )

        with col2:
            st.markdown("### 국가별 해당 관세율")
            if df_sel.empty:
                st.info("선택한 HS 코드에 해당하는 데이터가 없습니다.")
            else:
                df_sel_2025 = df_sel[df_sel["연도"] == 2025] if "연도" in df_sel.columns else pd.DataFrame()
                if df_sel_2025.empty:
                    st.info("2025년 데이터가 없어 국가별 조회를 표시할 수 없습니다.")
                else:
                    country_query = st.text_input("국가 검색", value="", placeholder="예: 미국, 일본, 중국...")
                    filtered = [c for c in COUNTRIES if country_query in c] if country_query else COUNTRIES
                    if not filtered:
                        st.warning("검색 결과가 없습니다. 다시 입력해주세요.")
                        filtered = COUNTRIES

                    sel_cty = st.selectbox("국가 선택", sorted(filtered))
                    if "국가" in df_sel_2025.columns and "적용국가구분" in df_sel_2025.columns:
                        base = df_sel_2025[df_sel_2025["적용국가구분"] == "1"]  # 전체 국가 공통
                        mask = (df_sel_2025["적용국가구분"] == "2") & token_match_country(df_sel_2025["국가"], sel_cty)
                        country_rows = df_sel_2025.loc[mask]
                        cut_cty = pd.concat([base, country_rows], ignore_index=True)
                        cut_cty = cut_cty.drop_duplicates(subset=[c for c in ["관세율구분값","관세율"] if c in cut_cty.columns])

                        cols_cty = [c for c in ["관세율구분","관세율구분값","관세율"] if c in cut_cty.columns]
                        if cut_cty.empty or not cols_cty:
                            st.info(f"{sel_cty} 관련 협정 데이터가 없습니다.")
                        else:
                            # 관세율 정렬 키 확보
                            sort_key = "관세율"
                            if "관세율_num" in cut_cty.columns:
                                sort_key = "관세율_num"
                            st.dataframe(
                                cut_cty[cols_cty].sort_values(sort_key),
                                use_container_width=True,
                                hide_index=True
                            )
                    else:
                        st.info("데이터에 '국가' 또는 '적용국가구분' 컬럼이 없습니다.")

    # =========================================
    # 연도별 추이
    # =========================================
    elif menu == "연도별 관세 추이":
        st.markdown("## 📌연도별 평균 관세율 조회")
        if df_sel.empty:
            st.info("선택한 HS 코드에 해당하는 데이터가 없습니다.")
            return

        if "관세율_num" not in df_sel.columns or "연도" not in df_sel.columns:
            st.info("연도별 평균을 계산할 수 있는 컬럼(관세율_num, 연도)이 부족합니다.")
            return

        col1, col2 = st.columns(2)
        grp = (
            df_sel.dropna(subset=["관세율_num"])
            .groupby("연도", as_index=False)["관세율_num"]
            .mean()
        )

        with col1:
            st.markdown("#### 연도별 평균 관세율")
            st.dataframe(
                grp.rename(columns={"관세율_num": "평균 관세율(%)"}),
                use_container_width=True,
                hide_index=True
            )

        with col2:
            st.markdown("### 연도별 평균 관세율 추이")
            if grp.empty:
                st.info("표시할 데이터가 없습니다.")
            else:
                fig = px.line(grp, x="연도", y="관세율_num", markers=True)
                fig.update_layout(yaxis_title="관세율(%)")
                st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()
