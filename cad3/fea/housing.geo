// cad3/fea/housing.geo - tet mesh of input/housing.step (2nd order, C3D10)
// act2 module frame: origin = back-face centre, +Z toward output.
// run:  $GMSH housing.geo -setnumber cl 4 -setnumber clh 2 -
// (writes run/housing_<cl>_<clh>.msh)
Merge "input/housing.step";
Mesh.ElementOrder = 2;
Mesh.CharacteristicLengthMax = cl;
Mesh.CharacteristicLengthFromCurvature = 1;
Mesh.MinimumElementsPerTwoPi = 24;
// tag the real reaction surfaces: the 41 ring-pin bores (R 23.5, d 3.05,
// z 33.5..43.5) - each bore wall selected by its own bounding box
ps() = {};
For k In {0:40}
  a = 2*Pi*k/41;
  bx = 23.5*Cos(a); by = 23.5*Sin(a);
  ps() += Surface In BoundingBox {bx-2.0, by-2.0, 33.4, bx+2.0, by+2.0, 43.6};
EndFor
Physical Surface("pinbores") = {ps()};
// fine at the ring-pin bores (torque reaction) and the back pilots (arm mount)
Field[1] = Ball;  Field[1].XCenter = 0.0;  Field[1].YCenter = 0.0;
Field[1].ZCenter = 38.5;  Field[1].Radius = 9.0;
Field[1].VIn = clh;  Field[1].VOut = cl;  Field[1].Thickness = 6.0;
Field[2] = Ball;  Field[2].XCenter = 0.0;  Field[2].YCenter = 0.0;
Field[2].ZCenter = 1.6;   Field[2].Radius = 27.0;
Field[2].VIn = clh;  Field[2].VOut = cl;  Field[2].Thickness = 6.0;
Field[9] = Min;  Field[9].FieldsList = {1, 2};
Background Field = 9;
Physical Volume("housing") = {Volume{:}};
Mesh 3;
Mesh.MshFileVersion = 2.2;
Save Sprintf("run/housing_%g_%g.msh", cl, clh);
Printf("GMSH DONE nodes=%g elems=%g", Mesh.NbNodes, 0);
Exit;
