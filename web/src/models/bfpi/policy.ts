/**
 * Sample policy for the shipped BFPI reference panel.
 *
 * Kept separate from the lab component so that consumers which only need the
 * constant (the bank explorer, the methodology page) do not pull the lab —
 * and its chart and stress-test UI — into their bundle.
 */

/**
 * Minimum number of computable pillars before a composite is published.
 * Below it, BFPI is withheld and the individual pillars are shown instead.
 */
export const MIN_PILLARS = 3;
