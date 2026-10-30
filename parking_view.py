"""Compact public parking cards shared by chat and the visit sidebar."""

import streamlit as st

from parking_tools import ParkingLookup, lookup_parking, map_search_url


def render_parking_help(initial: ParkingLookup, *, key: str, show_intro: bool = True) -> None:
    """A location follow-up uses the same reviewed tool without another AI call."""
    result_key = f"{key}_parking_result"
    context_key = f"{key}_parking_context"
    context = initial.model_dump_json()
    if st.session_state.get(context_key) != context:
        # A new visit/destination invalidates any prior manual parking search.
        for suffix in ("result", "choice", "query"):
            st.session_state.pop(f"{key}_parking_{suffix}", None)
        st.session_state[context_key] = context
    result = st.session_state.get(result_key, initial)
    st.markdown("**Parking & directions**")
    with st.form(f"{key}_parking_search", border=False):
        query = st.text_input(
            "Facility name or appointment address",
            placeholder="For example, 225 E. Chicago Avenue",
            max_chars=2000,
            key=f"{key}_parking_query",
        )
        searched = st.form_submit_button("Find parking", use_container_width=True)
    if searched:
        result = lookup_parking(query)
        st.session_state[result_key] = result
        # Clear a prior facility selection when the search changes.
        st.session_state.pop(f"{key}_parking_choice", None)

    if show_intro or searched or result is not initial:
        st.write(result.message)

    if result.status == "choose_location" and result.locations:
        choices = {location.location_id: location for location in result.locations}
        selected = st.selectbox(
            "Confirm the address on your appointment",
            options=list(choices),
            index=None,
            placeholder="Choose your appointment location",
            format_func=lambda item: f"{choices[item].name} · {choices[item].address}",
            key=f"{key}_parking_choice",
        )
        if selected:
            result = ParkingLookup(
                status="matched",
                message="Here are the published parking instructions for the location you selected.",
                locations=[choices[selected]],
            )

    if result.status == "matched":
        location = result.locations[0]
        with st.container(border=True):
            st.caption("APPOINTMENT LOCATION" if result.destination_source == "appointment" else "YOUR SELECTED DESTINATION")
            st.markdown(f"**{location.name}**")
            st.write(location.address)
            st.link_button("View hospital / clinic map", map_search_url(location.address), use_container_width=True)
        for option in location.options:
            with st.container(border=True):
                st.markdown(f"**🅿 {option.name}**")
                st.write(option.address)
                st.write(option.instructions)
                st.markdown(
                    f"[Map to this parking option]({map_search_url(option.address)})"
                    f" · [Official parking source]({option.source_url})"
                )
        provenance = "Destination supplied by your demo appointment record." if result.destination_source == "appointment" else "This lookup does not change or verify your appointment location."
        st.caption(f"Public information reviewed {location.checked_on:%B %d, %Y}. {provenance}")
        st.markdown(f"[Lurie's official location page]({location.source_url})")

    st.caption(result.availability_note)
    st.markdown(f"[Find other Lurie locations or search near you]({result.location_finder_url})")
