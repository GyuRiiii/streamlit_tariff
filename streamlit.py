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

# 파일 경로C:\Users\p\Desktop\인턴\streamlit\data\tariff_semi
tariff_path = "C:/Users/p/Desktop/인턴/streamlit/data/tariff_semi/tariff_semi_2020_with_info.csv"
hs_path = "C:/Users/p/Desktop/인턴/streamlit/data/unique_hscode_semi.csv"
base_dir = Path("C:/Users/p/Desktop/인턴/streamlit/data/tariff_semi")

YEARS = [2020, 2021, 2022, 2023, 2024, 2025]

# =========================================
# 유틸 함수
# =========================================
@st.cache_data
def load_data(): # 데이터 읽기
    df = pd.read_csv(tariff_path, dtype=str, encoding="utf-8-sig")
    return df

def load_data_all():
    dfs = []
    for y in YEARS:
        f = base_dir / f"tariff_semi_{y}_with_info.csv"
        if not f.exists():
            continue
        df = pd.read_csv(f, dtype=str, encoding="utf-8-sig")
        df["연도"] = y # 2020~2025 데이터 하나로 합치고 새로운 컬럼 "연도" 추가
        # 관세율 숫자형 변환
        if "관세율" in df.columns:
            df["관세율_num"] = pd.to_numeric(df["관세율"].str.replace(",",""), errors="coerce") # 문자열 -> 숫자 변환
        dfs.append(df)
    if dfs:
        return pd.concat(dfs, ignore_index=True)
    else:
        return pd.DataFrame()

def load_hs_list():
    df_hs = pd.read_csv(hs_path, encoding="utf-8-sig")
    # 컬럼명이 'HS코드' 또는 첫 컬럼일 수 있음
    col = "HS코드" if "HS코드" in df_hs.columns else df_hs.columns[0]
    hs_list = (
        df_hs[col].astype(str).dropna().str.strip().replace("", pd.NA).dropna().unique().tolist()
    )
    hs_list = sorted(set(hs_list))
    return hs_list


def token_match_country(series: pd.Series, country: str) -> pd.Series:
    """
    데이터 '국가' 셀이 '브라질 미국 중국' 식으로 공백 구분일 때,
    선택 국가가 토큰으로 포함되는 행만 True.
    """
    patt = re.compile(rf"(?:^|\s){re.escape(country)}(?:\s|$)")
    out = series.astype(str).str.replace(r"\s+", " ", regex=True).str.strip().apply(
        lambda s: bool(patt.search(s))
    )
    out.index = series.index   # ✅ 인덱스 강제 일치
    return out

def main():
    # =========================================
    # 데이터 로드
    # =========================================
    # try:
    #     df, hs_codes, loaded_path = load_data()
    # except Exception as e:
    #     st.error(f"데이터 로드 오류: {e}")
    #     st.stop()
    df = load_data_all()
    hs_list = load_hs_list()

    # =========================================
    # 사이드바
    # =========================================
    st.title("반도체 분야 관세율·협정 대시보드")
    st.sidebar.title("필터")
    
    # hs코드 검색 + 후보
    q = st.sidebar.text_input("HS 코드 검색", value="", placeholder="예: 8486, 8542, ...")
    if q:
        candidates = [h for h in hs_list if h.startswith(q)]
        if not candidates:
            st.sidebar.warning("해당 패턴으로 시작하는 HS 코드가 없습니다.")
            candidates = hs_list
    else:
        candidates = hs_list  # 너무 길면 UI가 무거워지므로 100개만 노출

    # HS코드 선택
    hs_selected = st.sidebar.selectbox("HS코드 선택", candidates)

    # 페이지 선택
    menu = st.sidebar.radio("페이지", ["수입 관세율 조회", "연도별 관세 추이", "관세 이슈 키워드(예정)", "주요 국가별 해외 관세(예정)", "무역 동향(예정)"])

    # =========================================
    # 홈
    # =========================================
    # if menu == "":
    #     if df.empty:
    #         st.error("데이터가 없습니다. 파일 경로를 확인하세요.")
    #         return

    #     # 선택한 HS 필터링
    #     if "품목번호" not in df.columns:
    #         st.error("데이터에 '품목번호' 컬럼이 없습니다.")
    #         return
    #     df_sel = df[df["품목번호"] == hs_selected]

    #     if df_sel.empty:
    #         st.warning("선택한 HS 코드에 해당하는 데이터가 없습니다.")
    #         return

    #     # 대표 품목명
    #     item_name = None
    #     for col in ["품명","품목명","이름","소분류","대분류"]:
    #         if col in df_sel.columns:
    #             vals = df_sel[col].dropna().unique()
    #             if len(vals) > 0:
    #                 item_name = vals[0]
    #                 break
    #     if item_name:
    #         st.markdown(f"**품목명:** {item_name}")


    # =========================================
    # 관세율 조회
    # =========================================
    if menu=="수입 관세율 조회":
                # 고정 국가 리스트
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

        df_sel = df[df["품목번호"] == hs_selected]


        st.markdown("## 📌수입 관세율 조회")
        col1, col2 = st.columns(2)
            
        # # ==== 표1 - 2025기준 적용 협정/관세율 (필요없을것같은디;;)
        with col1: 
            if df.empty:
                st.error("데이터가 없습니다. 파일 경로를 확인하세요.")
                return

            # 선택한 HS 필터링
            if "품목번호" not in df.columns:
                st.error("데이터에 '품목번호' 컬럼이 없습니다.")
                return
            df_sel = df[df["품목번호"] == hs_selected]

            if df_sel.empty:
                st.warning("선택한 HS 코드에 해당하는 데이터가 없습니다.")
                return

            # 대표 품목명
            item_name = None
            for col in ["품명","품목명","이름","소분류","대분류"]:
                if col in df_sel.columns:
                    vals = df_sel[col].dropna().unique()
                    if len(vals) > 0:
                        item_name = vals[0]
                        break
            if item_name:
                st.markdown(f"**품목명:** {item_name}")
            # st.markdown("## 📌수입 관세율 조회")
            df_sel_2025 = df_sel[df_sel["연도"] == 2025]
            st.markdown("### 2025년 관세 협정 / 관세율")
            show_cols = ["관세율구분값", "관세율"] # 보여줄 컬럼만 선택
            # 실제 데이터프레임에 해당 컬럼이 있는지 확인 후 추출
            available_cols = [c for c in show_cols if c in df_sel_2025.columns]
            st.dataframe(
                df_sel_2025[available_cols].sort_values(["관세율"]),
                use_container_width=True,
                hide_index=True
            )

        ###---------------------------
        #     min_rate = df_sel_2025["관세율_num"].min()
        #     df_min = df_sel_2025[df_sel_2025["관세율_num"] == min_rate]
        # # ====표2 - 최저세율 적용 국가들
        #     if "국가" in df_sel_2025.columns and "관세율_num" in df_sel_2025.columns:
        #         st.markdown("### 최저세율 적용 국가")
        #         # grp = (df_sel_2025.dropna(subset=["관세율_num"])
        #         #                 .groupby("국가", as_index=False)["관세율_num"].min()
        #         #                 .sort_values("관세율_num"))
        #         # st.dataframe(grp.rename(columns={"관세율_num":"최저 관세율(%)"}),
        #         #             use_container_width=True, hide_index=True)
        #         expanded_rows = []

        #         for _, row in df_min.iterrows():
        #             rate = row["관세율_num"]

        #             if str(row.get("적용국가구분")) == "1":  
        #                 # 전체 국가 공통 (COUNTRIES 전체 적용)
        #                 for c in COUNTRIES:
        #                     expanded_rows.append({"국가": c, "관세율_num": min_rate})

        #             elif str(row.get("적용국가구분")) == "2":  
        #                 # 특정 국가 리스트 풀기
        #                 countries = str(row.get("국가", "")).split()
        #                 for c in countries:
        #                     if c and c.lower() != "all" and c != "nan":
        #                         expanded_rows.append({"국가": c, "관세율_num": min_rate})

        #         df_expanded = pd.DataFrame(expanded_rows)

        #         if not df_expanded.empty:
        #             grp = (df_expanded.groupby("국가", as_index=False)["관세율_num"]
        #                                 .min()
        #                                 .sort_values("관세율_num"))
        #             st.dataframe(grp.rename(columns={"관세율_num":"최저 관세율(%)"}),
        #                         use_container_width=True, hide_index=True)
        #         else:
        #             st.info("적용 국가 데이터가 없습니다.")
        with col2:
            st.markdown("### ")
            # st.markdown("")
            # st.markdown("")
            st.markdown("### 국가별 해당 관세율")

            # 검색 입력창
            country_query = st.text_input("국가 검색", value="", placeholder="예: 미국, 일본, 중국...")
            # 검색 결과 필터링
            if country_query:
                filtered_countries = [c for c in COUNTRIES if country_query in c]
                if not filtered_countries:
                    st.warning("검색 결과가 없습니다. 다시 입력해주세요.")
                    filtered_countries = COUNTRIES
            else:
                filtered_countries = COUNTRIES
            
            
            sel_cty = st.selectbox("국가 선택", sorted(filtered_countries))
            if "국가" in df_sel_2025.columns:
                # 1) 기본세율 (모든 국가 공통)
                base = df_sel_2025[df_sel_2025["적용국가구분"] == "1"]
                # 2) 특정 국가 협정세율 (적용국가구분=2 + 국가 포함)
                mask = (df_sel_2025["적용국가구분"] == "2") & token_match_country(df_sel_2025["국가"], sel_cty)
                country_rows = df_sel_2025.loc[mask]
                # 3) 합치기 + 중복 제거
                cut_cty = pd.concat([base, country_rows], ignore_index=True)
                cut_cty = cut_cty.drop_duplicates(subset=["관세율구분값","관세율"])
                # 보여줄 컬럼
                cols_cty = [c for c in ["관세율구분","관세율구분값","관세율"] if c in cut_cty.columns]
                if cut_cty.empty:
                    st.info(f"{sel_cty} 관련 협정 데이터가 없습니다.")
                else:
                    st.dataframe(cut_cty[cols_cty].sort_values(["관세율"]),
                                use_container_width=True, hide_index=True)
            # mask = token_match_country(df_sel_2025["국가"], sel_cty)
            # cut_cty = df_sel_2025.loc[mask].copy()   # 이제 에러 안 남
            # cols_cty = [c for c in ["관세율구분","관세율구분값","관세율"] if c in cut_cty.columns]
            # if cut_cty.empty:
            #     st.info(f"{sel_cty} 관련 협정 데이터가 없습니다.")
            # else:
            #     st.dataframe(cut_cty[cols_cty].sort_values(["관세율구분값","관세율"]),
            #                  use_container_width=True, hide_index=True)



    # =========================================
    # 연도별 추이
    # =========================================
    elif menu=="연도별 관세 추이":
    
        

        st.markdown("## 📌연도별 평균 관세율 조회")
        if df.empty:
            st.error("데이터가 없습니다. 파일 경로를 확인하세요.")
            return

        # 선택한 HS 필터링
        if "품목번호" not in df.columns:
            st.error("데이터에 '품목번호' 컬럼이 없습니다.")
            return
        df_sel = df[df["품목번호"] == hs_selected]

        if df_sel.empty:
            st.warning("선택한 HS 코드에 해당하는 데이터가 없습니다.")
            return

        # 대표 품목명
        item_name = None
        for col in ["품명","품목명","이름","소분류","대분류"]:
            if col in df_sel.columns:
                vals = df_sel[col].dropna().unique()
                if len(vals) > 0:
                    item_name = vals[0]
                    break
        if item_name:
            st.markdown(f"**품목명:** {item_name}")
        col1, col2 = st.columns(2)
        with col1:

            # 연도별 평균 관세율 집계
            if "관세율" in df_sel.columns:
                grp = df_sel.groupby("연도", as_index=False)["관세율_num"].mean()
                st.markdown("#### 연도별 평균 관세율")
                st.dataframe(grp.rename(columns={"관세율_num":"평균 관세율(%)"}), use_container_width=True, hide_index=True)
        with col2:
            st.markdown("### 연도별 평균 관세율 추이")
            fig = px.line(grp, x="연도", y="관세율_num", markers=True)
                         # title="연도별 평균 관세율 추이")
            fig.update_layout(yaxis_title="관세율(%)")
            st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    main()