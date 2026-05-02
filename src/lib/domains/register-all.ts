/**
 * QCompass — Side-effect import that registers all seven scaffolding
 * domains with the registry. Importing this once is sufficient.
 *
 * Cosmology already self-registers via its own module
 * (`./cosmology.ucglef1`) which is imported by `domain-selector.tsx`.
 */
import "./chemistry";
import "./condmat";
import "./amo";
import "./hep";
import "./nuclear";
import "./gravity";
import "./statmech";
