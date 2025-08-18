import {
  ButtonItem,
  PanelSection,
  PanelSectionRow,
  Navigation,
  staticClasses,
  SidebarNavigation,
  Router,
  Field,
  ToggleField
} from "@decky/ui";
import {
  addEventListener,
  removeEventListener,
  definePlugin,
  toaster,
  routerHook,
} from "@decky/api"
import { FC, useEffect, useLayoutEffect, useState } from "react";
import { L, localizationManager } from "./i18n";
import { t } from "i18next";
import { About, Upgrade } from "./pages";
import { DeckyNatpierceIcon } from "./global";
import { ActionButtonItem, InstallationGuide } from "./components";
import { backend, Config, ResourceType } from "./backend";

function Content() {
  const localConfig: Config = JSON.parse(window.localStorage.getItem("decky-natpierce-config") || "{}");
  const localIP = window.localStorage.getItem("decky-natpierce-ip") || "";

  const [natpierceState, setNatpierceState] = useState(localConfig.status);
  const [natpierceStateChanging, setNatpierceStateChanging] = useState(false);
  const [installGuide, setInstallGuide] = useState(false);
  const [pluginVersion, setPluginVersion] = useState("");
  const [coreVersion, setCoreVersion] = useState("");
  const [natpierceStateTips, setNatpierceStateTips] = useState(
    localConfig.status ?
      t(L.ENABLE_NATPIERCE_IS_RUNNING) :
      t(L.ENABLE_NATPIERCE_DESC)
  );
  const [initialized, setInitialized] = useState(false);
  const [__, setCurrentIP] = useState<string>(localIP);
  const [autostart, setAutostart] = useState(localConfig.autostart);
  const [controllerPort, setControllerPort] = useState(localConfig.controller_port);

  // const restartNatPierce = async () => {
  //   if (!natpierceState)
  //     return;
  //   setNatpierceStateChanging(true);
  //   const success = await backend.restartCore();
  //   setNatpierceStateChanging(false);
  //   if (!success) {
  //     toaster.toast({
  //       title: t(L.RESTART_CORE),
  //       body: t(L.ENABLE_NATPIERCE_FAILED),
  //       icon: <DeckyNatpierceIcon />,
  //     });
  //   }
  // }

  const refreshVersions = async () => {
    const _coreVersion = await backend.getVersion(ResourceType.CORE);
    const _pluginVersion = await backend.getVersion(ResourceType.PLUGIN);
    setCoreVersion(_coreVersion);
    setPluginVersion(_pluginVersion);
    return [_coreVersion];
  };

  useEffect(() => {
    refreshVersions().then(([_coreVersion]) => {
      if (_coreVersion === "")
        setInstallGuide(true);
    });
  }, []);

  const applyConfig = (config: Config, save: boolean = true) => {
    if (save) {
      window.localStorage.setItem("decky-natpierce-config", JSON.stringify(config));
    }
    setNatpierceStateTips(
      config.status ?
        t(L.ENABLE_NATPIERCE_IS_RUNNING) :
        t(L.ENABLE_NATPIERCE_DESC)
    );
    setNatpierceState(config.status);
    setAutostart(config.autostart);
    setControllerPort(config.controller_port);
  }

  const fetchConfig = async () => {
    setInitialized(false);
    const config = await backend.getConfig();
    console.log(config);
    applyConfig(config);
    setInitialized(true);
  };

  const fetchIP = async () => {
    const ip = await backend.getIP();
    console.log(ip);
    setCurrentIP(ip);
    window.localStorage.setItem("decky-natpierce-ip", ip);
  };

  const fetchAllConfig = async () => {
    await Promise.all([
      fetchConfig(),
      fetchIP(),
    ]);
  }

  const getCurrentConfig = (): Config => {
    return {
      status: natpierceState,
      autostart: autostart,
      controller_port: controllerPort,
    };
  }

  useEffect(() => {
    if (initialized) {
      window.localStorage.setItem("decky-natpierce-config", JSON.stringify(getCurrentConfig()));
    }
  }, [initialized, natpierceState, autostart, controllerPort])

  useLayoutEffect(() => { fetchAllConfig(); }, []);

  return (installGuide ?
    <InstallationGuide
      coreVersion={coreVersion}
      refreshCallback={refreshVersions}
      quitCallback={() => setInstallGuide(false)}
    />
    :
    <>
      <PanelSection title={t(L.SERVICE)}>
        <PanelSectionRow>
          <ToggleField
            label={t(L.ENABLE_NATPIERCE)}
            description={natpierceStateTips}
            checked={natpierceState}
            disabled={natpierceStateChanging}
            onChange={async (value: boolean) => {
              setNatpierceState(value);
              setNatpierceStateChanging(true);
              setNatpierceStateTips(
                value ?
                  t(L.ENABLE_NATPIERCE_LOADING) :
                  t(L.ENABLE_NATPIERCE_DESC)
              );
              const [success, error] = await backend.setCoreStatus(value);
              setNatpierceStateChanging(false);
              if (!success) {
                setNatpierceState(false);
                toaster.toast({
                  title: t(L.ENABLE_NATPIERCE_FAILED),
                  body: error,
                  icon: <DeckyNatpierceIcon />,
                });
                setNatpierceStateTips(
                  t(L.ENABLE_NATPIERCE_FAILED) + " Err: " + error
                );
              } else {
                setNatpierceStateTips(
                  value ?
                    t(L.ENABLE_NATPIERCE_IS_RUNNING) :
                    t(L.ENABLE_NATPIERCE_DESC)
                );
              }
              backend.getCoreStatus().then(setNatpierceState);
            }}
          />
        </PanelSectionRow>
        <PanelSectionRow>
          <ButtonItem
            layout="below"
            onClick={() => {
              Router.CloseSideMenus();
              Navigation.NavigateToExternalWeb(
                `http://127.0.0.1:${controllerPort}`
              );
            }}
            disabled={natpierceStateChanging || !natpierceState}
          >
            {t(L.OPEN_DASHBOARD)}
          </ButtonItem>
        </PanelSectionRow>
        <PanelSectionRow>
          <ToggleField
            label={t(L.AUTOSTART)}
            description={t(L.AUTOSTART_DESC)}
            checked={autostart}
            onChange={(value: boolean) => {
              setAutostart(value);
              backend.setConfigValue("autostart", value).then(() =>
                backend.getConfigValue("autostart").then(setAutostart));
            }}
          ></ToggleField>
        </PanelSectionRow>
      </PanelSection>
      <PanelSection title={t(L.TOOLS)}>
        <PanelSectionRow>
          <ActionButtonItem
            layout="below"
            onClick={fetchAllConfig}
          >
            {t(L.RELOAD_CONFIG)}
          </ActionButtonItem>
        </PanelSectionRow>
        {/* <PanelSectionRow>
          <ActionButtonItem
            disabled={!natpierceState || natpierceStateChanging}
            layout="below"
            onClick={restartNatPierce}
          >
            {t(L.RESTART_CORE)}
          </ActionButtonItem>
        </PanelSectionRow> */}
      </PanelSection>
      <PanelSection title={t(L.VERSION)}>
        <PanelSectionRow>
          <Field
            focusable
            label={t(L.PLUGIN)}
          >
            {pluginVersion}
          </Field>
        </PanelSectionRow>
        <PanelSectionRow>
          <Field
            focusable
            label="NatPierce"
          >
            {coreVersion}
          </Field>
        </PanelSectionRow>
        <PanelSectionRow>
          <ButtonItem
            layout="below"
            onClick={() => {
              Router.CloseSideMenus();
              Router.Navigate("/decky-natpierce/upgrade");
            }}
          >
            {t(L.UPGRADE_MANAGE)}
          </ButtonItem>
        </PanelSectionRow>
        <PanelSectionRow>
          <ButtonItem
            layout="below"
            onClick={() => {
              Router.CloseSideMenus();
              Router.Navigate("/decky-natpierce/about");
            }}
          >
            {t(L.ABOUT_PLUGIN)}
          </ButtonItem>
        </PanelSectionRow>
      </PanelSection>
    </>
  );
};

const DeckyPluginRouter: FC = () => {
  return (
    <SidebarNavigation
      title="DeckyNatpierce"
      showTitle
      pages={[
        {
          title: t(L.UPGRADE),
          content: <Upgrade />,
          route: "/decky-natpierce/upgrade",
        },
        {
          title: t(L.ABOUT),
          content: <About />,
          route: "/decky-natpierce/about",
        },
      ]}
    />
  );
};

export default definePlugin(() => {
  localizationManager.init();
  routerHook.addRoute("/decky-natpierce", DeckyPluginRouter);

  const listener = addEventListener<[
    test1: string,
    test2: boolean,
    test3: number
  ]>("timer_event", (test1, test2, test3) => {
    console.log("Template got timer_event with:", test1, test2, test3)
    toaster.toast({
      title: "template got timer_event",
      body: `${test1}, ${test2}, ${test3}`
    });
  });

  return {
    name: "DeckyNatpierce",
    titleView: <div className={staticClasses.Title}>DeckyNatpierce</div>,
    content: <Content />,
    icon: <DeckyNatpierceIcon />,
    onDismount() {
      console.log("Unloading")
      removeEventListener("timer_event", listener);
    },
  };
});
