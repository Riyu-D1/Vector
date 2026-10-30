// fea_link/link.geo - tet mesh of input/link_fea.step (2nd order, C3D10)
// run:  cd fea_link && $GMSH link.geo -setnumber cl 5 -setnumber clh 2.5 -
// (writes run/link_<cl>_<clh>.msh; clh = target size inside the joint-end balls)
Merge "input/link_fea.step";
Mesh.ElementOrder = 2;
Mesh.CharacteristicLengthMax = cl;
Mesh.CharacteristicLengthFromCurvature = 1;
Mesh.MinimumElementsPerTwoPi = 24;
// finer at the joint ends (bolt circles, bearing seats, collars, fillets)
Field[1] = Ball;  Field[1].XCenter = 0.0;    Field[1].YCenter = 27.8;
Field[1].ZCenter = 0.0;  Field[1].Radius = 34.0;
Field[1].VIn = clh;  Field[1].VOut = cl;  Field[1].Thickness = 8.0;
Field[2] = Ball;  Field[2].XCenter = 126.7;  Field[2].YCenter = 27.8;
Field[2].ZCenter = 0.0;  Field[2].Radius = 34.0;
Field[2].VIn = clh;  Field[2].VOut = cl;  Field[2].Thickness = 8.0;
Field[9] = Min;  Field[9].FieldsList = {1, 2};
Background Field = 9;
Physical Volume("link") = {Volume{:}};
Mesh 3;
Mesh.MshFileVersion = 2.2;
Save Sprintf("run/link_%g_%g.msh", cl, clh);
Printf("GMSH DONE nodes=%g elems=%g", Mesh.NbNodes, Mesh.NbElements);
Exit;
