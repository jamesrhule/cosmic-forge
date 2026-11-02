/**
 * QCompass — Side-effect import that registers all seven scaffolding
 * domains with the registry. Importing this once is sufficient.
 *
 * Cosmology already self-registers via its own module
 * (`./cosmology.ucglef1`) which is imported by `domain-selector.tsx`.
 */
// Cosmology also self-registers when the domain selector loads; it is
// imported here too so any route that resolves a domain (e.g.
// `/domains/cosmology.ucglef1/visualizer/$id`) finds it regardless of
// module load order (P0-02).
import "./cosmology.ucglef1";
import "./chemistry";
import "./condmat";
import "./amo";
import "./hep";
import "./nuclear";
import "./gravity";
import "./statmech";
