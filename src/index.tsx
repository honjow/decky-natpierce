import {
  ButtonItem,
  PanelSection,
  PanelSectionRow,
  Navigation,
  staticClasses,
  SidebarNavigation,
  Router,
  Field,
  ToggleField,
  showModal,
  ConfirmModal,
  TextField,
} from "@decky/ui";
import {
  definePlugin,
  toaster,
  routerHook
} from "@decky/api"
import { FC, useEffect, useLayoutEffect, useState } from "react";
import { L, localizationManager } from "./i18n";
import { t } from "i18next";
import { About, Upgrade } from "./pages";
import { DeckyNatpierceIcon, DefautlPort } from "./global";
import { ActionButtonItem, InstallationGuide } from "./components";
import { backend, Config, ResourceType } from "./backend";
import { QRCodeCanvas } from "qrcode.react";

function Content() {
  const keyConfig = "decky-natpierce-config";
  const keyIP = "decky-natpierce-ip";
  const keyShowRemoteAccessQR = "decky-natpierce-show-remote-access-qr";

  const localConfig: Config = JSON.parse(window.localStorage.getItem(keyConfig) || "{}");
  const localIP = window.localStorage.getItem(keyIP) || "";
  const localShowRemoteAccessQR = window.localStorage.getItem(keyShowRemoteAccessQR) || "false";

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
  const [currentIP, setCurrentIP] = useState<string>(localIP);
  const [autostart, setAutostart] = useState(localConfig.autostart);
  const [controllerPort, setControllerPort] = useState(localConfig.controller_port);
  const [costomPort, setCostomPort] = useState(localConfig.costom_port);
  const [qrPageUrl, setQrPageUrl] = useState<string>("");
  const [showRemoteAccessQR, setShowRemoteAccessQR] = useState(Boolean(localShowRemoteAccessQR));

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
      window.localStorage.setItem(keyConfig, JSON.stringify(config));
    }
    setNatpierceStateTips(
      config.status ?
        t(L.ENABLE_NATPIERCE_IS_RUNNING) :
        t(L.ENABLE_NATPIERCE_DESC)
    );
    setNatpierceState(config.status);
    setAutostart(config.autostart);
    setControllerPort(config.controller_port);
    setCostomPort(config.costom_port);
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
    window.localStorage.setItem(keyIP, ip);
  };

  const fetchAllConfig = async () => {
    await Promise.all([
      fetchConfig(),
      fetchIP(),
    ]);
  }

  useEffect(() => {
    if (currentIP) {
      setQrPageUrl(`http://${currentIP}:${costomPort ? controllerPort : DefautlPort}`)
    }
  },
    [currentIP, controllerPort, costomPort]
  );

  const getCurrentConfig = (): Config => {
    return {
      status: natpierceState,
      autostart: autostart,
      controller_port: controllerPort,
      costom_port: costomPort,
    };
  }

  useEffect(() => {
    if (initialized) {
      window.localStorage.setItem(keyConfig, JSON.stringify(getCurrentConfig()));
    }
  }, [initialized, natpierceState, autostart, controllerPort, costomPort])

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
            label={t(L.SHOW_REMOTE_ACCESS_QR)}
            description=
            {(natpierceState && !natpierceStateChanging && qrPageUrl && showRemoteAccessQR) && (
              <div style={{ overflowWrap: "break-word" }}>
                <QRCodeCanvas style={{
                  display: "block",
                  margin: "8px auto",
                }} value={qrPageUrl} size={128} />
                {qrPageUrl}
              </div>
            )}
            checked={showRemoteAccessQR}
            disabled={natpierceStateChanging}
            onChange={(value: boolean) => {
              setShowRemoteAccessQR(value);
              window.localStorage.setItem(keyShowRemoteAccessQR, value.toString());
            }}
          ></ToggleField>
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
        <PanelSectionRow>
          <ToggleField
            label={t(L.COSTOM_PORT)}
            checked={costomPort}
            disabled={natpierceStateChanging || natpierceState}
            onChange={(value: boolean) => {
              setCostomPort(value);
              backend.setConfigValue("costom_port", value).then(() =>
                backend.getConfigValue("costom_port").then(setCostomPort));
            }}
          ></ToggleField>
        </PanelSectionRow>
        {costomPort && <PanelSectionRow>
          <ButtonItem
            layout="below"
            label={t(L.PORT_NUMBER)}
            disabled={!costomPort || natpierceStateChanging || natpierceState}
            description={t(L.PORT_RANGE_DESC)}
            onClick={() => {
              const PortInputModal = ({ closeModal }: { closeModal: () => void }) => {
                const [tempPort, setTempPort] = useState(controllerPort.toString());

                return (
                  <ConfirmModal
                    strTitle={t(L.PORT_NUMBER)}
                    strDescription={
                      <TextField
                        value={tempPort}
                        onChange={(e) => setTempPort(e.target.value)}
                        mustBeNumeric={true}
                        rangeMin={1}
                        rangeMax={65535}
                        description={t(L.PORT_RANGE_DESC)}
                        focusOnMount={true}
                      />
                    }
                    strOKButtonText={t(L.CONFIRM)}
                    strCancelButtonText={t(L.CANCEL)}
                    onOK={async () => {
                      const port = parseInt(tempPort);
                      if (!isNaN(port) && port >= 1 && port <= 65535) {
                        setControllerPort(port);
                        await backend.setConfigValue("controller_port", port);
                      }
                      closeModal();
                    }}
                    onCancel={() => {
                      closeModal();
                    }}
                    closeModal={closeModal}
                  />
                );
              };

              const modalResult = showModal(<PortInputModal closeModal={() => modalResult.Close()} />);
            }}
          >
            {controllerPort}
          </ButtonItem>
        </PanelSectionRow>}
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

  return {
    name: "DeckyNatpierce",
    titleView: <div className={staticClasses.Title}>DeckyNatpierce</div>,
    content: <Content />,
    icon: <DeckyNatpierceIcon />,
    onDismount() {
      console.log("Unloading")
    },
  };
});
