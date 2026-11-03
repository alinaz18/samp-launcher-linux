Name:           samp-launcher
Version:        %{pkg_version}
Release:        1%{?dist}
Summary:        SA-MP launcher for Linux
License:        MIT
URL:            https://github.com/alinaz18/samp-launcher-linux
Source0:        samp-launcher-%{version}.tar.gz
BuildArch:      noarch

Requires:       python3 >= 3.9
Requires:       python3-pyside6
Requires:       wine
Recommends:     winetricks

%description
Native Qt launcher for SA-MP (GTA San Andreas multiplayer): server browser,
favorites, nickname and a configurable game folder for mods. The Windows game
itself runs through a Wine prefix managed by the launcher.

%prep
%setup -q

%build

%install
bash packaging/stage.sh %{buildroot} %{_prefix}

%files
%license %{_datadir}/licenses/samp-launcher/LICENSE
%doc %{_datadir}/doc/samp-launcher/README.md
%doc %{_datadir}/doc/samp-launcher/README.en.md
%{_bindir}/samp-launcher
%{_datadir}/samp-launcher/
%{_datadir}/applications/samp-launcher.desktop
%{_datadir}/icons/hicolor/scalable/apps/samp-launcher.svg
