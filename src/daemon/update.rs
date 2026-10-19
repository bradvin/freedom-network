//! Compatibility handling for the inherited auto_update setting.
//! No polling, installer process, binary replacement or restart is permitted in this fork.

use anyhow::{Result, bail};

/// Old configurations may request updates. Refuse visibly without preventing ordinary daemon operation.
pub(super) fn configure(enabled: bool) -> Result<()> {
    if enabled {
        bail!("auto_update is disabled in this fork; use a reviewed source revision (see DISTRIBUTION.md)");
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    #[test]
    fn old_config_cannot_enable_binary_replacement() {
        let cfg: crate::config::Config = toml::from_str("auto_update = true").unwrap();
        let error = super::configure(cfg.auto_update).unwrap_err();
        assert!(error.to_string().contains("disabled"));
        assert!(super::configure(false).is_ok());
    }
}
