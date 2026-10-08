# Secondary model of q2-stage1-rescoped-v1 (S1a), registration section 10.1.
#
# Usage (inside the pinned CPU container, infra/q2-stage1/glmm/Dockerfile):
#   Rscript glmm.R <episodes.csv> <out.json> [n_boot] [seed]
#
# The CSV has one row per scored episode: y (0/1), size, harness, task, session, rerun.
# Session labels are nested in size (the caller writes "4B:S1", "9B:S2", ...).
#
# Model (logit, Laplace, glmmTMB):
#   y ~ size*harness + (1|task) + (1|task:size) + (1|task:harness) + (1|task:size:harness)
#       + (1|session) + (1|harness:session) + (1|task:session) + (1|task:harness:session)
#
# Reported:
#   * fixed effects, variance components and latent-scale shares
#     (component / (sum of components + pi^2/3));
#   * parametric-bootstrap percentile intervals for the shares (n_boot simulations from the
#     fitted model, each refitted; failed refits are counted and left out);
#   * the likelihood-ratio test of harness-specific task variance: the full model against the
#     model without (1|task:harness), both keeping (1|task:harness:session); chi-square with
#     1 df, and the boundary-corrected p/2 beside it;
#   * convergence: glmmTMB's optimizer code and pdHess for every fit. A fit that does not
#     converge is reported as such, never dropped silently.
suppressPackageStartupMessages({
  library(glmmTMB)
  library(jsonlite)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) stop("usage: Rscript glmm.R <episodes.csv> <out.json> [n_boot] [seed]")
in_csv <- args[[1]]
out_json <- args[[2]]
n_boot <- if (length(args) >= 3) as.integer(args[[3]]) else 200L
seed <- if (length(args) >= 4) as.integer(args[[4]]) else 42L

full_formula <- y ~ size * harness + (1 | task) + (1 | task:size) + (1 | task:harness) +
  (1 | task:size:harness) + (1 | session) + (1 | harness:session) + (1 | task:session) +
  (1 | task:harness:session)
reduced_formula <- y ~ size * harness + (1 | task) + (1 | task:size) +
  (1 | task:size:harness) + (1 | session) + (1 | harness:session) + (1 | task:session) +
  (1 | task:harness:session)

read_episodes <- function(path) {
  d <- read.csv(path, stringsAsFactors = FALSE)
  need <- c("y", "size", "harness", "task", "session")
  missing <- setdiff(need, names(d))
  if (length(missing) > 0) stop(paste("missing columns:", paste(missing, collapse = ", ")))
  d <- d[!is.na(d$y), ]
  if (!all(d$y %in% c(0, 1))) stop("y must be 0 or 1")
  for (col in c("size", "harness", "task", "session")) d[[col]] <- factor(d[[col]])
  d
}

fit_model <- function(formula, data) {
  fit <- tryCatch(
    suppressWarnings(glmmTMB(formula, data = data, family = binomial(link = "logit"))),
    error = function(e) e
  )
  fit
}

fit_status <- function(fit) {
  if (inherits(fit, "error")) {
    return(list(ok = FALSE, error = conditionMessage(fit)))
  }
  list(
    ok = isTRUE(fit$fit$convergence == 0) && isTRUE(fit$sdr$pdHess),
    optimizer_convergence = fit$fit$convergence,
    optimizer_message = fit$fit$message,
    pdHess = isTRUE(fit$sdr$pdHess),
    logLik = as.numeric(logLik(fit)),
    df = attr(logLik(fit), "df")
  )
}

variance_components <- function(fit) {
  vc <- VarCorr(fit)$cond
  out <- sapply(names(vc), function(name) as.numeric(vc[[name]][1, 1]))
  out
}

shares <- function(components) {
  total <- sum(components) + pi^2 / 3
  components / total
}

d <- read_episodes(in_csv)
set.seed(seed)
full <- fit_model(full_formula, d)
reduced <- fit_model(reduced_formula, d)
result <- list(
  schema = "q2-stage1a-glmm-v1",
  formula_full = paste(deparse(full_formula, width.cutoff = 500), collapse = " "),
  formula_reduced = paste(deparse(reduced_formula, width.cutoff = 500), collapse = " "),
  n_episodes = nrow(d),
  n_tasks = nlevels(d$task),
  seed = seed,
  n_boot = n_boot,
  glmmTMB_version = as.character(packageVersion("glmmTMB")),
  TMB_version = as.character(packageVersion("TMB")),
  R_version = R.version.string,
  full = fit_status(full),
  reduced = fit_status(reduced)
)

if (!inherits(full, "error")) {
  comps <- variance_components(full)
  result$fixed_effects <- as.list(fixef(full)$cond)
  result$variance_components <- as.list(comps)
  result$latent_shares <- as.list(shares(comps))
  if (n_boot > 0) {
    sims <- simulate(full, nsim = n_boot, seed = seed)
    boot <- matrix(NA_real_, nrow = n_boot, ncol = length(comps))
    colnames(boot) <- names(comps)
    failed <- 0L
    not_converged <- 0L
    for (b in seq_len(n_boot)) {
      db <- d
      db$y <- as.numeric(sims[[b]])
      fb <- fit_model(full_formula, db)
      if (inherits(fb, "error")) {
        failed <- failed + 1L
        next
      }
      status <- fit_status(fb)
      if (!isTRUE(status$ok)) not_converged <- not_converged + 1L
      cb <- variance_components(fb)
      boot[b, names(cb)] <- shares(cb)
    }
    usable <- boot[stats::complete.cases(boot), , drop = FALSE]
    result$bootstrap <- list(
      refits_failed = failed,
      refits_not_converged = not_converged,
      refits_used = nrow(usable),
      shares_ci95 = lapply(colnames(boot), function(name) {
        if (nrow(usable) == 0) return(NULL)
        as.numeric(stats::quantile(usable[, name], c(0.025, 0.975), names = FALSE))
      })
    )
    names(result$bootstrap$shares_ci95) <- colnames(boot)
  }
}

if (!inherits(full, "error") && !inherits(reduced, "error")) {
  stat <- 2 * (as.numeric(logLik(full)) - as.numeric(logLik(reduced)))
  p <- stats::pchisq(max(stat, 0), df = 1, lower.tail = FALSE)
  result$lrt_task_harness <- list(
    statistic = stat,
    df = 1,
    p_value = p,
    p_value_boundary_corrected = p / 2,
    both_converged = isTRUE(result$full$ok) && isTRUE(result$reduced$ok)
  )
}

writeLines(toJSON(result, auto_unbox = TRUE, digits = NA, null = "null", na = "null",
                  pretty = TRUE), out_json)
