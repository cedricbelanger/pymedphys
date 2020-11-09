from pymedphys._imports import pandas as pd, xmltodict
from pymedphys._imports import streamlit as st


from pymedphys._streamlit.apps.wlutz import _dbf


@st.cache()
def calc_filepath_from_frames_dbid(dbid_series):
    return [f"img/{f'{dbid:0>8x}'.upper()}.jpg" for dbid in dbid_series]


def dbf_frame_based_database(database_directory, refresh_cache, filtered_table):
    frame = _dbf.load_dbf(database_directory, refresh_cache, "frame")
    with_frame = filtered_table.merge(frame, left_on="PIMG_DBID", right_on="PIMG_DBID")

    delta = pd.to_timedelta(with_frame["DELTA_MS"], unit="ms")
    timestamps = with_frame["datetime"] + delta

    with_frame["time"] = timestamps.dt.time
    with_frame["datetime"] = timestamps

    with_frame.sort_values("datetime", ascending=False, inplace=True)

    filepaths = calc_filepath_from_frames_dbid(with_frame["FRAME_DBID"])
    with_frame["filepath"] = filepaths
    with_frame = with_frame[
        [
            "filepath",
            "time",
            "machine_id",
            "patient_id",
            "treatment",
            "port",
            "datetime",
            "PIMG_DBID",
        ]
    ]

    return with_frame


@st.cache()
def calc_xml_filepaths(table):
    return (
        "patient_"
        + table["patient_id"].astype("str")
        + "/MV_IMAGES/img_"
        + table["DICOM_UID"].astype("str")
        + "/_Frame.xml"
    )


@st.cache()
def load_xml(filepath):
    with open(filepath) as fd:
        doc = xmltodict.parse(fd.read())

    return doc


@st.cache()
def data_from_doc(doc):
    table_rows = []

    projection_set = doc["ProjectionSet"]
    dicom_uid = projection_set["Image"]["DicomUID"]

    frames = projection_set["Frames"]["Frame"]

    if isinstance(frames, dict):
        sequence = frames["Seq"]
        delta_ms = frames["DeltaMs"]

        table_rows.append(
            {"sequence": sequence, "delta_ms": delta_ms, "DICOM_UID": dicom_uid}
        )
    elif isinstance(frames, list):
        for frame in frames:
            sequence = frame["Seq"]
            delta_ms = frame["DeltaMs"]

            table_rows.append(
                {"sequence": sequence, "delta_ms": delta_ms, "DICOM_UID": dicom_uid}
            )
    else:
        raise ValueError("Unexpected type of frame")

    return table_rows


def xml_frame_based_database(database_directory, filtered_table):
    xml_filepaths = calc_xml_filepaths(filtered_table)

    xml_docs = [
        load_xml(database_directory.joinpath(filepath)) for filepath in xml_filepaths
    ]
    frame_table_rows = []
    for doc in xml_docs:
        frame_table_rows += data_from_doc(doc)

    frame_table = pd.DataFrame.from_dict(frame_table_rows)

    merged = filtered_table.merge(
        frame_table, left_on="DICOM_UID", right_on="DICOM_UID"
    )
    st.write(merged)

    st.stop()
