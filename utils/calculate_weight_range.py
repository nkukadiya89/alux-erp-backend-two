from decimal import Decimal


def get_weight_range(die_profile_wt_kg_p_mt, length, tolerance):
    """Calculate the weight range based on the given tolerance."""

    # Calculate per piece weight
    per_piece_weight = (die_profile_wt_kg_p_mt * length) / Decimal(
        1000
    )  # Convert to kg

    # Determine the tolerance percentage
    tolerance_mapping = {
        "Zero(0)": Decimal(0),
        "+-3%": Decimal(0.03),
        "+3%": Decimal(0.03),
        "+-5%": Decimal(0.05),
        "+5%": Decimal(0.05),
        "+-7%": Decimal(0.07),
        "+7%": Decimal(0.07),
        "+-10%": Decimal(0.10),
        "+10%": Decimal(0.10),
        "-3%": Decimal(-0.03),
        "-5%": Decimal(-0.05),
        "-7%": Decimal(-0.07),
        "-10%": Decimal(-0.10),
    }

    tolerance_percentage = tolerance_mapping.get(
        tolerance, Decimal(0)
    )  # Default to 0 if tolerance not found

    # Calculate the weight range
    lower_bound = per_piece_weight - (per_piece_weight * tolerance_percentage)
    upper_bound = per_piece_weight + (per_piece_weight * tolerance_percentage)

    # Format as a string
    return f"{lower_bound:.3f} - {upper_bound:.3f}"


def get_quatation_weight_range(die_profile_wt_kg_p_mt, length, tolerance):
    """Calculate the weight range based on the given tolerance."""

    # Calculate per piece weight
    per_piece_weight = (die_profile_wt_kg_p_mt * length) / Decimal(
        1000
    )  # Convert to kg

    # Determine the tolerance percentage
    tolerance_mapping = {
        "+-10%": Decimal(0.10),
        "+10%": Decimal(0.10),
    }

    tolerance_percentage = tolerance_mapping.get(
        tolerance, Decimal(0)
    )  # Default to 0 if tolerance not found

    # Calculate the weight range
    lower_bound = per_piece_weight - (per_piece_weight * tolerance_percentage)
    upper_bound = per_piece_weight + (per_piece_weight * tolerance_percentage)

    # Format as a string
    return f"{lower_bound:.3f} - {upper_bound:.3f}"
